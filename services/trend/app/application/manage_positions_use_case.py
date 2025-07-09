"""Use case for managing open trading positions."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from ..domain.entities import TrendPosition, PositionStatus
from ..domain.interfaces import (
    IPositionManager, ITrendRepository, IExchangeService,
    INotificationService, IRiskManager
)

logger = logging.getLogger(__name__)


class ManagePositionsUseCase:
    """Caso de uso para gestionar las posiciones abiertas."""
    
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
        
    async def execute(self) -> int:
        """
        Gestiona todas las posiciones abiertas.
        
        Returns:
            Número de posiciones procesadas
        """
        try:
            # Obtener todas las posiciones abiertas
            open_positions = await self.repository.get_open_positions()
            
            if not open_positions:
                logger.debug("No hay posiciones abiertas para gestionar")
                return 0
            
            logger.info(f"Gestionando {len(open_positions)} posiciones abiertas")
            
            processed_count = 0
            
            for position in open_positions:
                try:
                    # Obtener precio actual
                    current_price = await self.exchange_service.get_current_price(
                        position.symbol
                    )
                    
                    # Actualizar posición con precio actual
                    position = await self.position_manager.update_position(
                        position, current_price
                    )
                    
                    # Verificar condiciones de salida
                    exit_reason = await self.position_manager.check_exit_conditions(
                        position, current_price
                    )
                    
                    if exit_reason:
                        logger.info(
                            f"Cerrando posición {position.id} para {position.symbol}: "
                            f"{exit_reason}"
                        )
                        
                        # Cerrar la posición
                        closed_position = await self._close_position(position, exit_reason)
                        
                        if closed_position:
                            # Actualizar métricas
                            await self._update_metrics(closed_position)
                            processed_count += 1
                    else:
                        # Actualizar trailing stop si está configurado
                        if position.trailing_stop_distance:
                            new_stop = position.update_trailing_stop(current_price)
                            if new_stop:
                                await self.repository.save_position(position)
                                logger.info(
                                    f"Trailing stop actualizado para {position.symbol}: "
                                    f"{new_stop}"
                                )
                        
                        # Guardar posición actualizada
                        await self.repository.save_position(position)
                        
                        # Log estado actual
                        pnl = position.unrealized_pnl()
                        pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
                        
                        logger.debug(
                            f"Posición {position.symbol}: PnL={pnl:.2f} ({pnl_percent:+.2f}%), "
                            f"Precio actual={current_price}"
                        )
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(
                        f"Error gestionando posición {position.id}: {str(e)}",
                        exc_info=True
                    )
                    await self.notification_service.send_error_alert(
                        f"Error gestionando posición {position.symbol}",
                        {"position_id": position.id, "error": str(e)}
                    )
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error en gestión de posiciones: {str(e)}", exc_info=True)
            await self.notification_service.send_error_alert(
                "Error crítico en gestión de posiciones",
                {"error": str(e)}
            )
            return 0
    
    async def check_position_health(self, position_id: str) -> Optional[str]:
        """
        Verifica la salud de una posición específica.
        
        Args:
            position_id: ID de la posición a verificar
            
        Returns:
            Mensaje de estado o None si la posición es saludable
        """
        try:
            position = await self.repository.get_position_by_id(position_id)
            
            if not position:
                return "Posición no encontrada"
            
            if position.status != PositionStatus.OPEN:
                return f"Posición no está abierta: {position.status.value}"
            
            # Obtener precio actual
            current_price = await self.exchange_service.get_current_price(position.symbol)
            
            # Calcular PnL
            position.current_price = current_price
            pnl = position.unrealized_pnl()
            pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
            
            # Verificar si está en pérdida significativa
            max_loss_percent = -10.0  # -10% máxima pérdida
            if pnl_percent < max_loss_percent:
                return f"Pérdida excesiva: {pnl_percent:.2f}%"
            
            # Verificar tiempo de retención
            holding_hours = (datetime.utcnow() - position.entry_time).total_seconds() / 3600
            max_holding_hours = 72  # 3 días máximo
            
            if holding_hours > max_holding_hours:
                return f"Posición abierta demasiado tiempo: {holding_hours:.1f} horas"
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando salud de posición: {str(e)}", exc_info=True)
            return f"Error verificando posición: {str(e)}"
    
    async def _close_position(
        self, 
        position: TrendPosition, 
        reason: str
    ) -> Optional[TrendPosition]:
        """Cierra una posición y actualiza el estado."""
        try:
            # Cerrar posición en el exchange
            closed_position = await self.position_manager.close_position(position, reason)
            
            # Guardar posición cerrada
            await self.repository.save_position(closed_position)
            
            # Notificar cierre
            await self.notification_service.send_position_closed(closed_position, reason)
            
            # Log resultado
            pnl = closed_position.realized_pnl()
            pnl_percent = float(pnl / (closed_position.entry_price * closed_position.entry_quantity) * 100)
            
            logger.info(
                f"Posición cerrada - {closed_position.symbol}: "
                f"PnL={pnl:.2f} ({pnl_percent:+.2f}%), "
                f"Razón={reason}"
            )
            
            return closed_position
            
        except Exception as e:
            logger.error(
                f"Error cerrando posición {position.id}: {str(e)}",
                exc_info=True
            )
            await self.notification_service.send_error_alert(
                f"Error crítico cerrando posición {position.symbol}",
                {"position_id": position.id, "error": str(e)}
            )
            return None
    
    async def _update_metrics(self, position: TrendPosition) -> None:
        """Actualiza las métricas con una posición cerrada."""
        try:
            # Obtener métricas actuales
            metrics = await self.repository.get_metrics(position.symbol)
            
            if not metrics:
                from ..domain.entities import TrendMetrics
                metrics = TrendMetrics()
            
            # Actualizar con la posición cerrada
            metrics.update_from_position(position)
            
            # Guardar métricas actualizadas
            await self.repository.save_metrics(position.symbol, metrics)
            
            logger.debug(
                f"Métricas actualizadas para {position.symbol}: "
                f"Total trades={metrics.total_trades}, "
                f"Win rate={metrics.win_rate:.2%}"
            )
            
        except Exception as e:
            logger.error(
                f"Error actualizando métricas: {str(e)}",
                exc_info=True
            ) 