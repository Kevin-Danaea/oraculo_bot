"""Use case for the main trend bot operation cycle."""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..domain.entities import (
    TrendBotState, BrainDecision, ExitReason, TrendPosition,
    TradingResult, TrendBotStatus, BrainDirective, TrendBotConfig
)
from ..domain.interfaces import (
    ITrendBotRepository, IBrainDirectiveRepository, IExchangeService,
    INotificationService, ITrendBotStateManager
)

logger = logging.getLogger(__name__)


class TrendBotCycleUseCase:
    """Caso de uso para el ciclo principal de operación del trend bot."""
    
    def __init__(
        self,
        repository: ITrendBotRepository,
        brain_repository: IBrainDirectiveRepository,
        exchange_service: IExchangeService,
        notification_service: INotificationService,
        state_manager: ITrendBotStateManager,
        config: TrendBotConfig
    ):
        self.repository = repository
        self.brain_repository = brain_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.state_manager = state_manager
        self.config = config
        self.bot_id = f"trend_bot_{config.symbol}_{uuid.uuid4().hex[:8]}"
        
    async def execute_cycle(self) -> bool:
        """
        Ejecuta un ciclo completo de operación del trend bot.
        
        Returns:
            True si el ciclo se ejecutó correctamente, False en caso contrario
        """
        try:
            logger.info(f"🔄 Iniciando ciclo de operación para {self.config.symbol}")
            
            # 1. Obtener estado actual del bot
            bot_status = await self._get_or_initialize_bot_status()
            
            # 2. Obtener directiva del cerebro
            brain_directive = await self._get_brain_directive()
            if not brain_directive:
                logger.warning("No se pudo obtener directiva del cerebro")
                return False
            
            # 3. Obtener precio actual
            current_price = self._get_current_price()
            if not current_price:
                logger.error("No se pudo obtener precio actual")
                return False
            
            # 4. Ejecutar lógica según estado actual
            success = await self._execute_state_logic(
                bot_status, brain_directive, current_price
            )
            
            # 5. Actualizar estado
            bot_status.last_update = datetime.utcnow()
            await self.state_manager.save_state(bot_status)
            
            logger.info(f"✅ Ciclo completado para {self.config.symbol}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de operación: {str(e)}", exc_info=True)
            await self.notification_service.send_error_notification(
                f"Error en ciclo de operación: {str(e)}",
                {"symbol": self.config.symbol, "bot_id": self.bot_id}
            )
            return False
    
    async def _get_or_initialize_bot_status(self) -> TrendBotStatus:
        """Obtiene o inicializa el estado del bot."""
        bot_status = await self.state_manager.get_state(self.bot_id)
        
        if not bot_status:
            logger.info(f"🆕 Inicializando nuevo bot para {self.config.symbol}")
            bot_status = await self.state_manager.initialize_state(self.bot_id, self.config)
            await self.notification_service.send_startup_notification(self.config)
        
        return bot_status
    
    async def _get_brain_directive(self) -> Optional[BrainDirective]:
        """Obtiene la última directiva del cerebro."""
        try:
            directive = await self.brain_repository.get_latest_directive(self.config.symbol)
            
            if directive and directive.is_valid():
                logger.debug(
                    f"Directiva del cerebro: {directive.decision.value} "
                    f"para {directive.symbol}"
                )
                return directive
            else:
                logger.warning("Directiva del cerebro no válida o no encontrada")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo directiva del cerebro: {str(e)}")
            return None
    
    def _get_current_price(self) -> Optional[Decimal]:
        """Obtiene el precio actual del símbolo."""
        try:
            price = self.exchange_service.get_current_price(self.config.symbol)
            logger.debug(f"Precio actual de {self.config.symbol}: {price}")
            return price
        except Exception as e:
            logger.error(f"Error obteniendo precio actual: {str(e)}")
            return None
    
    async def _execute_state_logic(
        self,
        bot_status: TrendBotStatus,
        brain_directive: BrainDirective,
        current_price: Decimal
    ) -> bool:
        """Ejecuta la lógica según el estado actual del bot."""
        
        if bot_status.state == TrendBotState.FUERA_DEL_MERCADO:
            return await self._handle_outside_market_state(
                bot_status, brain_directive, current_price
            )
        elif bot_status.state == TrendBotState.EN_POSICION:
            return await self._handle_in_position_state(
                bot_status, brain_directive, current_price
            )
        else:
            logger.error(f"Estado desconocido: {bot_status.state}")
            return False
    
    async def _handle_outside_market_state(
        self,
        bot_status: TrendBotStatus,
        brain_directive: BrainDirective,
        current_price: Decimal
    ) -> bool:
        """Maneja el estado FUERA_DEL_MERCADO."""
        
        if brain_directive.decision == BrainDecision.INICIAR_COMPRA_TENDENCIA:
            logger.info(f"🚀 Iniciando compra de tendencia para {self.config.symbol}")
            
            # Ejecutar orden de compra
            buy_result = self._execute_buy_order(current_price)
            
            if buy_result.success:
                # Crear posición
                if buy_result.executed_price and buy_result.executed_quantity:
                    position = TrendPosition(
                        id=str(uuid.uuid4()),
                        symbol=self.config.symbol,
                        entry_price=buy_result.executed_price,
                        entry_quantity=buy_result.executed_quantity,
                        entry_time=datetime.utcnow(),
                        highest_price_since_entry=buy_result.executed_price,
                        current_price=current_price,
                        fees_paid=buy_result.fees
                    )
                else:
                    logger.error("Orden ejecutada pero sin precio o cantidad")
                    return False
                
                # Actualizar estado del bot
                bot_status.state = TrendBotState.EN_POSICION
                bot_status.current_position = position
                bot_status.last_decision = brain_directive.decision
                
                # Guardar posición
                await self.repository.save_position(position)
                
                # Notificar apertura de posición
                await self.notification_service.send_position_opened(
                    position, self.config
                )
                
                logger.info(f"✅ Posición abierta: {position.entry_quantity} @ {position.entry_price}")
                return True
            else:
                logger.error(f"❌ Error ejecutando orden de compra: {buy_result.error_message}")
                await self.notification_service.send_error_notification(
                    f"Error ejecutando orden de compra: {buy_result.error_message}",
                    {"symbol": self.config.symbol, "price": str(current_price)}
                )
                return False
        
        elif brain_directive.decision == BrainDecision.MANTENER_POSICION:
            logger.debug("Manteniendo estado fuera del mercado")
            return True
        
        elif brain_directive.decision == BrainDecision.MANTENER_ESPERA:
            logger.debug("Manteniendo espera fuera del mercado")
            return True
        
        else:
            logger.debug(f"Directiva no aplicable en estado fuera del mercado: {brain_directive.decision}")
            return True
    
    async def _handle_in_position_state(
        self,
        bot_status: TrendBotStatus,
        brain_directive: BrainDirective,
        current_price: Decimal
    ) -> bool:
        """Maneja el estado EN_POSICION."""
        
        if not bot_status.current_position:
            logger.error("Bot en posición pero sin posición actual")
            return False
        
        position = bot_status.current_position
        position.current_price = current_price
        
        # Actualizar precio más alto si es necesario
        position.update_highest_price(current_price)
        
        # Verificar trailing stop
        trailing_stop_price = position.calculate_trailing_stop(
            self.config.trailing_stop_percent
        )
        
        if current_price <= trailing_stop_price:
            logger.info(f"🛑 Trailing stop activado: {current_price} <= {trailing_stop_price}")
            
            # Ejecutar orden de venta
            sell_result = self._execute_sell_order(position.entry_quantity)
            
            if sell_result.success:
                # Actualizar posición
                position.exit_price = sell_result.executed_price
                position.exit_quantity = sell_result.executed_quantity
                position.exit_time = datetime.utcnow()
                position.exit_reason = ExitReason.TRAILING_STOP
                position.fees_paid += sell_result.fees
                
                # Actualizar estado del bot
                bot_status.state = TrendBotState.FUERA_DEL_MERCADO
                bot_status.current_position = None
                bot_status.last_decision = brain_directive.decision
                
                # Guardar posición actualizada
                await self.repository.save_position(position)
                
                # Notificar salida por trailing stop
                await self.notification_service.send_trailing_stop_exit(
                    position, current_price, trailing_stop_price
                )
                
                # Actualizar métricas
                await self._update_metrics(position)
                
                logger.info(f"✅ Posición cerrada por trailing stop: PnL = {position.realized_pnl()}")
                return True
            else:
                logger.error(f"❌ Error ejecutando orden de venta: {sell_result.error_message}")
                return False
        
        # Verificar directiva del cerebro
        if brain_directive.decision == BrainDecision.CERRAR_POSICION:
            logger.info(f"📉 Cerrando posición por señal del cerebro")
            
            # Ejecutar orden de venta
            sell_result = self._execute_sell_order(position.entry_quantity)
            
            if sell_result.success:
                # Actualizar posición
                position.exit_price = sell_result.executed_price
                position.exit_quantity = sell_result.executed_quantity
                position.exit_time = datetime.utcnow()
                position.exit_reason = ExitReason.SEÑAL_CEREBRO
                position.fees_paid += sell_result.fees
                
                # Actualizar estado del bot
                bot_status.state = TrendBotState.FUERA_DEL_MERCADO
                bot_status.current_position = None
                bot_status.last_decision = brain_directive.decision
                
                # Guardar posición actualizada
                await self.repository.save_position(position)
                
                # Notificar salida por señal del cerebro
                await self.notification_service.send_brain_signal_exit(
                    position, brain_directive
                )
                
                # Actualizar métricas
                await self._update_metrics(position)
                
                logger.info(f"✅ Posición cerrada por señal del cerebro: PnL = {position.realized_pnl()}")
                return True
            else:
                logger.error(f"❌ Error ejecutando orden de venta: {sell_result.error_message}")
                return False
        
        elif brain_directive.decision == BrainDecision.MANTENER_POSICION:
            # Solo actualizar posición con precio actual
            await self.repository.save_position(position)
            logger.debug(f"Posición mantenida: PnL no realizado = {position.unrealized_pnl()}")
            return True
        
        else:
            logger.debug(f"Directiva no aplicable en posición: {brain_directive.decision}")
            return True
    
    def _execute_buy_order(self, current_price: Decimal) -> TradingResult:
        """Ejecuta una orden de compra a mercado."""
        try:
            # Calcular cantidad a comprar
            quantity = self.config.capital_allocation / current_price
            
            logger.info(f"Ejecutando compra: {quantity} {self.config.symbol} @ ~{current_price}")
            
            result = self.exchange_service.place_market_buy_order(
                self.config.symbol, quantity
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando orden de compra: {str(e)}")
            return TradingResult(
                success=False,
                error_message=str(e)
            )
    
    def _execute_sell_order(self, quantity: Decimal) -> TradingResult:
        """Ejecuta una orden de venta a mercado."""
        try:
            logger.info(f"Ejecutando venta: {quantity} {self.config.symbol}")
            
            result = self.exchange_service.place_market_sell_order(
                self.config.symbol, quantity
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando orden de venta: {str(e)}")
            return TradingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _update_metrics(self, position: TrendPosition) -> None:
        """Actualiza las métricas con una posición cerrada."""
        try:
            from ..domain.entities import TrendBotMetrics
            
            # Obtener métricas actuales
            metrics = await self.repository.get_metrics(self.bot_id)
            if not metrics:
                metrics = TrendBotMetrics()
            
            # Actualizar con la posición cerrada
            metrics.update_from_trade(position)
            
            # Guardar métricas actualizadas
            await self.repository.save_metrics(self.bot_id, metrics)
            
            logger.debug(f"Métricas actualizadas: {metrics.total_trades} trades, {metrics.win_rate:.1%} win rate")
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {str(e)}")
    
    async def check_trailing_stop(self) -> None:
        """Verifica y aplica trailing stop si es necesario."""
        try:
            # Obtener estado actual del bot
            bot_status = await self.state_manager.get_state(self.bot_id)
            
            if not bot_status or not bot_status.current_position:
                return  # No hay posición abierta
            
            # Obtener precio actual
            current_price = self._get_current_price()
            if not current_price:
                logger.warning("No se pudo obtener precio actual para trailing stop")
                return
            
            position = bot_status.current_position
            position.current_price = current_price
            
            # Actualizar precio más alto si es necesario
            position.update_highest_price(current_price)
            
            # Verificar trailing stop
            trailing_stop_price = position.calculate_trailing_stop(
                self.config.trailing_stop_percent
            )
            
            if current_price <= trailing_stop_price:
                logger.info(f"🛑 Trailing stop activado: {current_price} <= {trailing_stop_price}")
                
                # Ejecutar orden de venta
                sell_result = self._execute_sell_order(position.entry_quantity)
                
                if sell_result.success:
                    # Actualizar posición
                    position.exit_price = sell_result.executed_price
                    position.exit_quantity = sell_result.executed_quantity
                    position.exit_time = datetime.utcnow()
                    position.exit_reason = ExitReason.TRAILING_STOP
                    position.fees_paid += sell_result.fees
                    
                    # Actualizar estado del bot
                    bot_status.state = TrendBotState.FUERA_DEL_MERCADO
                    bot_status.current_position = None
                    bot_status.last_decision = BrainDecision.CERRAR_POSICION
                    
                    # Guardar estado y posición
                    await self.state_manager.save_state(bot_status)
                    await self.repository.save_position(position)
                    
                    # Notificar salida por trailing stop
                    await self.notification_service.send_trailing_stop_exit(
                        position, current_price, trailing_stop_price
                    )
                    
                    # Actualizar métricas
                    await self._update_metrics(position)
                    
                    logger.info(f"✅ Posición cerrada por trailing stop: PnL = {position.realized_pnl()}")
                else:
                    logger.error(f"❌ Error ejecutando orden de venta por trailing stop: {sell_result.error_message}")
            else:
                logger.debug(f"Trailing stop OK: {current_price} > {trailing_stop_price}")
                
        except Exception as e:
            logger.error(f"Error verificando trailing stop: {str(e)}", exc_info=True) 