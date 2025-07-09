"""Use case for executing trades based on signals."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from ..domain.entities import TrendSignal, TrendPosition, PositionStatus
from ..domain.interfaces import (
    IPositionManager, ITrendRepository, IExchangeService,
    INotificationService, IRiskManager
)

logger = logging.getLogger(__name__)


class ExecuteTradesUseCase:
    """Caso de uso para ejecutar operaciones de trading basadas en señales."""
    
    def __init__(
        self,
        position_manager: IPositionManager,
        repository: ITrendRepository,
        exchange_service: IExchangeService,
        notification_service: INotificationService,
        risk_manager: IRiskManager
    ):
        self.position_manager = position_manager
        self.repository = repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.risk_manager = risk_manager
        
    async def execute(self, symbol: Optional[str] = None) -> int:
        """
        Ejecuta trades basados en señales activas.
        
        Args:
            symbol: Símbolo específico para ejecutar trades (opcional)
            
        Returns:
            Número de trades ejecutados
        """
        try:
            # Obtener estrategias activas
            if symbol:
                strategy = await self.repository.get_strategy(symbol)
                strategies = [strategy] if strategy and strategy.enabled else []
            else:
                strategies = await self.repository.get_all_strategies(enabled_only=True)
            
            if not strategies:
                logger.debug("No hay estrategias activas para ejecutar trades")
                return 0
            
            trades_executed = 0
            
            for strategy in strategies:
                try:
                    # Verificar posiciones abiertas
                    open_positions = await self.repository.get_open_positions(strategy.symbol)
                    
                    if len(open_positions) >= strategy.max_positions:
                        logger.debug(
                            f"{strategy.symbol}: Máximo de posiciones alcanzado "
                            f"({len(open_positions)}/{strategy.max_positions})"
                        )
                        continue
                    
                    # Obtener señales activas
                    signals = await self.repository.get_active_signals(strategy.symbol)
                    valid_signals = [s for s in signals if s.is_valid()]
                    
                    if not valid_signals:
                        logger.debug(f"No hay señales válidas para {strategy.symbol}")
                        continue
                    
                    # Tomar la señal más reciente
                    signal = max(valid_signals, key=lambda s: s.timestamp)
                    
                    # Verificar si ya existe una posición para esta señal
                    existing_position = await self._has_position_for_signal(signal.id)
                    if existing_position:
                        logger.debug(
                            f"Ya existe una posición para la señal {signal.id}"
                        )
                        continue
                    
                    # Obtener balance disponible
                    quote_asset = self._get_quote_asset(strategy.symbol)
                    available_balance = await self.exchange_service.get_balance(quote_asset)
                    
                    # Validar señal con gestión de riesgo
                    if not await self.risk_manager.validate_signal(
                        signal, strategy, available_balance
                    ):
                        logger.info(
                            f"Señal {signal.id} rechazada por gestión de riesgo"
                        )
                        continue
                    
                    # Calcular tamaño de posición
                    position_size = await self.risk_manager.calculate_position_size(
                        signal, strategy, available_balance
                    )
                    
                    if position_size < strategy.min_position_size:
                        logger.warning(
                            f"Tamaño de posición calculado ({position_size}) "
                            f"menor al mínimo ({strategy.min_position_size})"
                        )
                        continue
                    
                    # Ejecutar el trade
                    position = await self._execute_trade(
                        signal, strategy, position_size
                    )
                    
                    if position:
                        trades_executed += 1
                        logger.info(
                            f"Trade ejecutado exitosamente: {position.symbol} "
                            f"{position.side} {position.entry_quantity} @ {position.entry_price}"
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Error ejecutando trades para {strategy.symbol}: {str(e)}",
                        exc_info=True
                    )
                    await self.notification_service.send_error_alert(
                        f"Error ejecutando trade para {strategy.symbol}",
                        {"error": str(e)}
                    )
            
            return trades_executed
            
        except Exception as e:
            logger.error(f"Error en ejecución de trades: {str(e)}", exc_info=True)
            await self.notification_service.send_error_alert(
                "Error crítico en ejecución de trades",
                {"error": str(e)}
            )
            return 0
    
    async def _has_position_for_signal(self, signal_id: str) -> bool:
        """Verifica si ya existe una posición para una señal."""
        open_positions = await self.repository.get_open_positions()
        return any(pos.signal_id == signal_id for pos in open_positions)
    
    async def _execute_trade(
        self,
        signal: TrendSignal,
        strategy,  # TrendStrategy
        position_size: Decimal
    ) -> Optional[TrendPosition]:
        """Ejecuta un trade basado en una señal."""
        try:
            # Crear posición
            position = await self.position_manager.open_position(signal, strategy)
            
            # Si la posición se abrió exitosamente, actualizar con detalles
            if position and position.status == PositionStatus.OPEN:
                # Calcular stop loss y take profit basados en la estrategia
                position.stop_loss = await self.risk_manager.calculate_stop_loss(
                    position.entry_price,
                    signal.direction,
                    strategy
                )
                
                position.take_profit = await self.risk_manager.calculate_take_profit(
                    position.entry_price,
                    position.stop_loss,
                    signal.direction,
                    strategy
                )
                
                # Si hay trailing stop configurado
                if strategy.trailing_stop_percentage:
                    position.trailing_stop_distance = (
                        position.entry_price * Decimal(strategy.trailing_stop_percentage / 100)
                    )
                
                # Guardar posición actualizada
                await self.repository.save_position(position)
                
                # Notificar apertura de posición
                await self.notification_service.send_position_opened(position)
                
                return position
            
            return None
            
        except Exception as e:
            logger.error(
                f"Error ejecutando trade para señal {signal.id}: {str(e)}",
                exc_info=True
            )
            await self.notification_service.send_error_alert(
                f"Error ejecutando trade para {signal.symbol}",
                {"signal_id": signal.id, "error": str(e)}
            )
            return None
    
    def _get_quote_asset(self, symbol: str) -> str:
        """Extrae el activo cotizado del símbolo."""
        # Asumiendo formato como BTCUSDT, ETHBUSD, etc.
        if symbol.endswith("USDT"):
            return "USDT"
        elif symbol.endswith("BUSD"):
            return "BUSD"
        elif symbol.endswith("BTC"):
            return "BTC"
        elif symbol.endswith("ETH"):
            return "ETH"
        else:
            # Por defecto USDT
            return "USDT" 