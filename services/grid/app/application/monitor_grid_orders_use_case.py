"""
Caso de uso principal para monitorear órdenes de grid trading.
Se ejecuta cada hora para verificar el estado de los bots.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder, GridBotState, TradingDecision, GridTrade
from app.config import MIN_ORDER_VALUE_USDT
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class MonitorGridOrdersUseCase:
    """
    Caso de uso principal que monitorea todas las órdenes de grid trading activas
    y ejecuta las acciones necesarias cada hora.
    """
    
    def __init__(
        self,
        grid_repository: GridRepository,
        exchange_service: ExchangeService,
        notification_service: NotificationService,
        grid_calculator: GridCalculator
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.grid_calculator = grid_calculator
        logger.info("✅ MonitorGridOrdersUseCase inicializado.")

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta el monitoreo completo de todos los bots de grid trading.
        
        Returns:
            Dict con el resultado del monitoreo
        """
        logger.info("🔄 ========== INICIANDO MONITOREO DE GRID TRADING ==========")
        
        try:
            # 1. Obtener todas las configuraciones activas de la base de datos
            active_configs = self.grid_repository.get_active_configs()
            
            if not active_configs:
                logger.info("ℹ️ No hay configuraciones activas para monitorear")
                return {
                    'success': True,
                    'monitored_bots': 0,
                    'actions_taken': [],
                    'message': 'No hay bots activos'
                }
            
            logger.info(f"📊 Monitoreando {len(active_configs)} configuraciones activas")
            
            # 2. Procesar cada configuración
            results = []
            for config in active_configs:
                try:
                    result = self._monitor_single_bot(config)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Error monitoreando bot {config.pair}: {e}")
                    results.append({
                        'pair': config.pair,
                        'success': False,
                        'error': str(e)
                    })
            
            # 3. Generar resumen
            successful_monitors = sum(1 for r in results if r.get('success', False))
            total_actions = sum(len(r.get('actions', [])) for r in results)
            
            logger.info(f"✅ Monitoreo completado: {successful_monitors}/{len(active_configs)} bots, {total_actions} acciones")
            
            return {
                'success': True,
                'monitored_bots': len(active_configs),
                'successful_monitors': successful_monitors,
                'total_actions': total_actions,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo de grid trading: {e}")
            self.notification_service.send_error_notification("Grid Trading Monitor", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    def _monitor_single_bot(self, config: GridConfig) -> Dict[str, Any]:
        """
        Monitorea un bot individual de grid trading.
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con el resultado del monitoreo
        """
        logger.info(f"🤖 Monitoreando bot {config.pair}...")
        
        actions = []
        
        try:
            # 1. Obtener precio actual
            current_price = self.exchange_service.get_current_price(config.pair)
            logger.info(f"💰 Precio actual {config.pair}: ${current_price}")
            
            # 2. Obtener órdenes activas de la base de datos
            active_orders = self.grid_repository.get_active_orders(config.pair)
            logger.info(f"📋 Órdenes activas para {config.pair}: {len(active_orders)}")
            
            # 3. Verificar estado de órdenes en el exchange
            filled_orders = self._check_filled_orders(active_orders)
            
            # 4. Procesar órdenes completadas
            if filled_orders:
                trades = self._process_filled_orders(filled_orders, config)
                for trade in trades:
                    self.notification_service.send_trade_notification(trade)
                    actions.append(f"Trade completado: {trade.profit:.4f} USDT")
            
            # 5. Crear nuevas órdenes si es necesario
            new_orders = self._create_missing_orders(config, current_price, active_orders)
            if new_orders:
                actions.extend([f"Nueva orden: {o.side} a ${o.price}" for o in new_orders])
            
            # 6. Actualizar estado del bot en la base de datos
            self._update_bot_state(config, current_price, active_orders)
            
            logger.info(f"✅ Bot {config.pair} monitoreado: {len(actions)} acciones")
            
            return {
                'pair': config.pair,
                'success': True,
                'current_price': float(current_price),
                'active_orders': len(active_orders),
                'filled_orders': len(filled_orders),
                'new_orders': len(new_orders) if new_orders else 0,
                'actions': actions
            }
            
        except Exception as e:
            logger.error(f"❌ Error monitoreando bot {config.pair}: {e}")
            return {
                'pair': config.pair,
                'success': False,
                'error': str(e)
            }

    def _check_filled_orders(self, active_orders: List[GridOrder]) -> List[GridOrder]:
        """Verifica qué órdenes han sido completadas en el exchange."""
        filled_orders = []
        
        for order in active_orders:
            if order.status == 'open' and order.exchange_order_id:
                try:
                    # Verificar estado en el exchange
                    order_status = self.exchange_service.get_order_status(order.pair, order.exchange_order_id)
                    
                    if order_status.get('status') == 'closed':
                        # Actualizar estado en la base de datos
                        self.grid_repository.update_order_status(
                            order.exchange_order_id, 
                            'filled',
                            datetime.now()
                        )
                        order.status = 'filled'
                        order.filled_at = datetime.now()
                        filled_orders.append(order)
                        
                        logger.info(f"✅ Orden completada: {order.side} {order.amount} {order.pair} a ${order.price}")
                        
                except Exception as e:
                    logger.error(f"❌ Error verificando orden {order.exchange_order_id}: {e}")
                    continue
        
        return filled_orders

    def _process_filled_orders(self, filled_orders: List[GridOrder], config: GridConfig) -> List[GridTrade]:
        """Procesa órdenes completadas y crea órdenes complementarias."""
        trades = []
        
        for order in filled_orders:
            try:
                if order.side == 'buy':
                    # Crear orden de venta complementaria
                    sell_price = self._calculate_sell_price(order.price, config)
                    sell_order = self._create_sell_order(order, sell_price, config)
                    
                    if sell_order:
                        logger.info(f"🔄 Orden de compra completada, creando venta a ${sell_price}")
                        
                elif order.side == 'sell':
                    # Crear orden de compra complementaria
                    buy_price = self._calculate_buy_price(order.price, config)
                    buy_order = self._create_buy_order(order, buy_price, config)
                    
                    if buy_order:
                        logger.info(f"🔄 Orden de venta completada, creando compra a ${buy_price}")
                        
                        # Calcular ganancia de este ciclo
                        profit = self._calculate_trade_profit(order, buy_order)
                        if profit > 0:
                            trade = GridTrade(
                                pair=order.pair,
                                buy_order_id=buy_order.exchange_order_id or '',
                                sell_order_id=order.exchange_order_id or '',
                                buy_price=buy_order.price,
                                sell_price=order.price,
                                amount=order.amount,
                                profit=profit,
                                profit_percent=(profit / (order.price * order.amount)) * 100,
                                executed_at=datetime.now()
                            )
                            trades.append(trade)
                            
            except Exception as e:
                logger.error(f"❌ Error procesando orden completada {order.exchange_order_id}: {e}")
                continue
        
        return trades

    def _calculate_sell_price(self, buy_price: Decimal, config: GridConfig) -> Decimal:
        """Calcula precio de venta basado en el precio de compra y la configuración."""
        spread_percent = config.price_range_percent / config.grid_levels
        return buy_price * (1 + Decimal(spread_percent / 100))

    def _calculate_buy_price(self, sell_price: Decimal, config: GridConfig) -> Decimal:
        """Calcula precio de compra basado en el precio de venta y la configuración."""
        spread_percent = config.price_range_percent / config.grid_levels
        return sell_price * (1 - Decimal(spread_percent / 100))

    def _create_sell_order(self, buy_order: GridOrder, sell_price: Decimal, config: GridConfig) -> Optional[GridOrder]:
        """Crea una orden de venta complementaria."""
        try:
            order_value = sell_price * buy_order.amount
            min_value = Decimal(MIN_ORDER_VALUE_USDT)
            
            if order_value < min_value:
                logger.warning(f"⚠️ Valor de orden muy pequeño: ${order_value} < ${min_value}")
                return None
            
            order = self.exchange_service.create_order(
                pair=buy_order.pair,
                side='sell',
                amount=buy_order.amount,
                price=sell_price,
                order_type='limit'
            )
            
            saved_order = self.grid_repository.save_order(order)
            logger.info(f"✅ Orden de venta creada: {order.amount} {order.pair} a ${sell_price}")
            
            return saved_order
            
        except Exception as e:
            logger.error(f"❌ Error creando orden de venta: {e}")
            return None

    def _create_buy_order(self, sell_order: GridOrder, buy_price: Decimal, config: GridConfig) -> Optional[GridOrder]:
        """Crea una orden de compra complementaria."""
        try:
            order_value = buy_price * sell_order.amount
            min_value = Decimal(MIN_ORDER_VALUE_USDT)
            
            if order_value < min_value:
                logger.warning(f"⚠️ Valor de orden muy pequeño: ${order_value} < ${min_value}")
                return None
            
            order = self.exchange_service.create_order(
                pair=sell_order.pair,
                side='buy',
                amount=sell_order.amount,
                price=buy_price,
                order_type='limit'
            )
            
            saved_order = self.grid_repository.save_order(order)
            logger.info(f"✅ Orden de compra creada: {order.amount} {order.pair} a ${buy_price}")
            
            return saved_order
            
        except Exception as e:
            logger.error(f"❌ Error creando orden de compra: {e}")
            return None

    def _create_missing_orders(self, config: GridConfig, current_price: Decimal, existing_orders: List[GridOrder]) -> List[GridOrder]:
        """Crea órdenes faltantes para mantener la grilla completa."""
        new_orders = []
        
        try:
            grid_levels = self.grid_calculator.calculate_grid_levels(current_price, config)
            
            buy_price = self.grid_calculator.should_create_buy_order(current_price, existing_orders, grid_levels)
            if buy_price:
                buy_order = self._create_order_at_price(config, 'buy', buy_price, current_price)
                if buy_order:
                    new_orders.append(buy_order)
            
            sell_price = self.grid_calculator.should_create_sell_order(current_price, existing_orders, grid_levels)
            if sell_price:
                sell_order = self._create_order_at_price(config, 'sell', sell_price, current_price)
                if sell_order:
                    new_orders.append(sell_order)
                    
        except Exception as e:
            logger.error(f"❌ Error creando órdenes faltantes para {config.pair}: {e}")
        
        return new_orders

    def _create_order_at_price(self, config: GridConfig, side: str, price: Decimal, current_price: Decimal) -> Optional[GridOrder]:
        """Crea una orden a un precio específico."""
        try:
            amount = self.grid_calculator.calculate_order_amount(
                config.total_capital, 
                config.grid_levels, 
                current_price
            )
            
            order_value = price * amount
            if order_value < Decimal(MIN_ORDER_VALUE_USDT):
                logger.warning(f"⚠️ Valor de orden muy pequeño: ${order_value}")
                return None
            
            if side == 'sell':
                base_currency = config.pair.split('/')[0]
                balance = self.exchange_service.get_balance(base_currency)
                if balance < amount:
                    logger.warning(f"⚠️ Balance insuficiente para venta: {balance} < {amount}")
                    return None
            
            order = self.exchange_service.create_order(
                pair=config.pair,
                side=side,
                amount=amount,
                price=price,
                order_type='limit'
            )
            
            return self.grid_repository.save_order(order)
            
        except Exception as e:
            logger.error(f"❌ Error creando orden {side} a ${price}: {e}")
            return None

    def _calculate_trade_profit(self, sell_order: GridOrder, buy_order: GridOrder) -> Decimal:
        """Calcula la ganancia de un trade completado."""
        try:
            sell_value = sell_order.price * sell_order.amount
            buy_value = buy_order.price * buy_order.amount
            return sell_value - buy_value
        except Exception:
            return Decimal('0')

    def _update_bot_state(self, config: GridConfig, current_price: Decimal, active_orders: List[GridOrder]) -> None:
        """Actualiza el estado del bot en la base de datos."""
        try:
            grid_levels = self.grid_calculator.calculate_grid_levels(current_price, config)
            upper_bound = max(grid_levels) if grid_levels else current_price
            lower_bound = min(grid_levels) if grid_levels else current_price
            
            bot_state = GridBotState(
                pair=config.pair,
                config=config,
                active_orders=active_orders,
                total_profit=Decimal('0'),
                total_trades=0,
                current_price=current_price,
                grid_upper_bound=upper_bound,
                grid_lower_bound=lower_bound,
                is_active=True,
                last_update=datetime.now()
            )
            
            self.grid_repository.save_bot_state(bot_state)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estado del bot {config.pair}: {e}") 