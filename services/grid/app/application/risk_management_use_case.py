"""
Caso de uso para gestión de riesgos: Stop Loss y Trailing Up.
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class RiskManagementUseCase:
    """
    Caso de uso para gestionar stop loss y trailing up en Grid Trading.
    
    Responsabilidades:
    - Verificar activación de stop loss (4% por defecto)
    - Verificar activación de trailing up (5% por defecto)
    - Ejecutar acciones de protección de capital
    - Notificar eventos de riesgo
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
        logger.info("✅ RiskManagementUseCase inicializado.")

    def check_and_handle_risk_events(self, config: GridConfig) -> Dict[str, Any]:
        """
        Verifica y maneja eventos de riesgo para un bot específico.
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con información de eventos de riesgo manejados
        """
        try:
            pair = config.pair
            current_price = self.exchange_service.get_current_price(pair)
            active_orders = self.grid_repository.get_active_orders(pair)
            
            events_handled = []
            
            # 1. Verificar Stop Loss
            if config.enable_stop_loss:
                stop_loss_event = self._check_stop_loss(config, current_price, active_orders)
                if stop_loss_event:
                    events_handled.append(stop_loss_event)
            
            # 2. Verificar Trailing Up
            if config.enable_trailing_up:
                trailing_up_event = self._check_trailing_up(config, current_price, active_orders)
                if trailing_up_event:
                    events_handled.append(trailing_up_event)
            
            if events_handled:
                logger.info(f"🚨 Eventos de riesgo manejados para {pair}: {len(events_handled)} eventos")
                return {
                    'success': True,
                    'pair': pair,
                    'events_handled': events_handled,
                    'current_price': float(current_price)
                }
            else:
                return {
                    'success': True,
                    'pair': pair,
                    'events_handled': [],
                    'current_price': float(current_price)
                }
                
        except Exception as e:
            logger.error(f"❌ Error verificando eventos de riesgo para {config.pair}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _check_stop_loss(self, config: GridConfig, current_price: Decimal, active_orders: List[GridOrder]) -> Optional[Dict[str, Any]]:
        """
        Verifica si se debe activar el stop loss.
        
        Returns:
            Dict con información del evento de stop loss o None
        """
        try:
            # Obtener precio de la última compra
            last_buy_price = self.grid_calculator.get_last_buy_price(active_orders)
            
            if not last_buy_price:
                return None
            
            # Verificar si se activa stop loss
            if self.grid_calculator.check_stop_loss_triggered(current_price, last_buy_price, config):
                logger.warning(f"🚨 STOP LOSS ACTIVADO para {config.pair}")
                
                # Ejecutar stop loss
                result = self._execute_stop_loss(config, current_price)
                
                # Notificar evento de riesgo
                self.notification_service.send_risk_event_notification(
                    event_type='stop_loss',
                    pair=config.pair,
                    details={
                        'last_buy_price': float(last_buy_price),
                        'current_price': float(current_price),
                        'drop_percent': float((last_buy_price - current_price) / last_buy_price * 100)
                    }
                )
                
                return {
                    'type': 'stop_loss',
                    'triggered': True,
                    'last_buy_price': float(last_buy_price),
                    'current_price': float(current_price),
                    'drop_percent': float((last_buy_price - current_price) / last_buy_price * 100),
                    'actions_taken': result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error verificando stop loss para {config.pair}: {e}")
            return None

    def _check_trailing_up(self, config: GridConfig, current_price: Decimal, active_orders: List[GridOrder]) -> Optional[Dict[str, Any]]:
        """
        Verifica si se debe activar el trailing up.
        
        Returns:
            Dict con información del evento de trailing up o None
        """
        try:
            # Obtener precio más alto de venta
            highest_sell_price = self.grid_calculator.get_highest_sell_price(active_orders)
            
            if not highest_sell_price:
                return None
            
            # Verificar si se activa trailing up
            if self.grid_calculator.check_trailing_up_triggered(current_price, highest_sell_price, config):
                logger.info(f"📈 TRAILING UP ACTIVADO para {config.pair}")
                
                # Ejecutar trailing up
                result = self._execute_trailing_up(config, current_price)
                
                # Notificar evento de riesgo
                self.notification_service.send_risk_event_notification(
                    event_type='trailing_up',
                    pair=config.pair,
                    details={
                        'highest_sell_price': float(highest_sell_price),
                        'current_price': float(current_price),
                        'rise_percent': float((current_price - highest_sell_price) / highest_sell_price * 100)
                    }
                )
                
                return {
                    'type': 'trailing_up',
                    'triggered': True,
                    'highest_sell_price': float(highest_sell_price),
                    'current_price': float(current_price),
                    'rise_percent': float((current_price - highest_sell_price) / highest_sell_price * 100),
                    'actions_taken': result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error verificando trailing up para {config.pair}: {e}")
            return None

    def _execute_stop_loss(self, config: GridConfig, current_price: Decimal) -> Dict[str, Any]:
        """
        Ejecuta las acciones de stop loss.
        
        Returns:
            Dict con información de acciones ejecutadas
        """
        try:
            pair = config.pair
            actions = []
            
            # 1. Cancelar todas las órdenes activas
            active_orders = self.grid_repository.get_active_orders(pair)
            cancelled_orders = 0
            
            for order in active_orders:
                if order.exchange_order_id and order.status == 'open':
                    try:
                        success = self.exchange_service.cancel_order(pair, order.exchange_order_id)
                        if success:
                            cancelled_orders += 1
                    except Exception as e:
                        logger.error(f"❌ Error cancelando orden {order.exchange_order_id}: {e}")
            
            actions.append(f"Canceladas {cancelled_orders} órdenes activas")
            
            # 2. Liquidar posiciones
            base_currency = pair.split('/')[0]
            base_balance = self.exchange_service.get_balance(base_currency)
            
            if base_balance > 0:
                try:
                    # Crear orden de mercado para vender todo
                    sell_order = self.exchange_service.create_order(
                        pair=pair,
                        side='sell',
                        amount=base_balance,
                        price=current_price,
                        order_type='market'
                    )
                    actions.append(f"Vendidas {base_balance} {base_currency} al mercado")
                except Exception as e:
                    logger.error(f"❌ Error liquidando posiciones: {e}")
                    actions.append("Error liquidando posiciones")
            
            # 3. Actualizar estado del bot
            if config.id is not None:
                self.grid_repository.update_config_status(
                    config.id,
                    is_running=False,
                    last_decision='STOP_LOSS_ACTIVATED'
                )
                actions.append("Bot pausado por stop loss")
            
            logger.warning(f"🛑 Stop loss ejecutado para {pair}: {', '.join(actions)}")
            
            return {
                'cancelled_orders': cancelled_orders,
                'positions_liquidated': base_balance > 0,
                'bot_paused': True,
                'actions': actions
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando stop loss para {config.pair}: {e}")
            return {
                'error': str(e),
                'actions': []
            }

    def _execute_trailing_up(self, config: GridConfig, current_price: Decimal) -> Dict[str, Any]:
        """
        Ejecuta las acciones de trailing up.
        
        Returns:
            Dict con información de acciones ejecutadas
        """
        try:
            pair = config.pair
            actions = []
            
            # 1. Cancelar todas las órdenes activas
            active_orders = self.grid_repository.get_active_orders(pair)
            cancelled_orders = 0
            
            for order in active_orders:
                if order.exchange_order_id and order.status == 'open':
                    try:
                        success = self.exchange_service.cancel_order(pair, order.exchange_order_id)
                        if success:
                            cancelled_orders += 1
                    except Exception as e:
                        logger.error(f"❌ Error cancelando orden {order.exchange_order_id}: {e}")
            
            actions.append(f"Canceladas {cancelled_orders} órdenes activas")
            
            # 2. Reinicializar grid con nuevo precio base
            # Obtener balance actual para reinicializar
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            allocated_capital = bot_balance['allocated_capital']
            half_capital = allocated_capital / Decimal(2)
            
            # Comprar 50% del capital al nuevo precio
            base_currency = pair.split('/')[0]
            amount_market = (half_capital / current_price).quantize(Decimal('0.000001'))
            
            try:
                market_order = self.exchange_service.create_order(
                    pair=pair,
                    side='buy',
                    amount=amount_market,
                    price=current_price,
                    order_type='market'
                )
                
                # Obtener cantidad real llenada
                if market_order.exchange_order_id:
                    status = self.exchange_service.get_order_status(pair, market_order.exchange_order_id)
                else:
                    status = {'filled': amount_market}
                
                filled_amount_gross = Decimal(str(status.get('filled', amount_market)))
                filled_amount_net = self.exchange_service.calculate_net_amount_after_fees(
                    gross_amount=filled_amount_gross,
                    price=current_price,
                    side='buy',
                    pair=pair
                )
                
                actions.append(f"Comprados {filled_amount_net} {base_currency} al nuevo precio ${current_price}")
                
                # 3. Crear nueva grilla con el nuevo precio base
                grid_levels = self.grid_calculator.calculate_grid_levels(current_price, config)
                lower_levels = [p for p in grid_levels if p < current_price]
                upper_levels = [p for p in grid_levels if p > current_price]
                
                min_len = min(len(lower_levels), len(upper_levels))
                lower_levels = lower_levels[-min_len:]
                upper_levels = upper_levels[:min_len]
                
                amount_per_order = self.grid_calculator.calculate_order_amount(
                    total_capital=float(half_capital),
                    grid_levels=len(lower_levels),
                    current_price=current_price
                )
                
                amount_sell_each = (filled_amount_net / Decimal(len(upper_levels))).quantize(Decimal('0.000001'))
                
                new_orders_created = 0
                for buy_price, sell_price in zip(lower_levels, upper_levels):
                    # Crear orden de compra
                    buy_order = self.exchange_service.create_order(
                        pair=pair,
                        side='buy',
                        amount=amount_per_order,
                        price=buy_price,
                        order_type='limit'
                    )
                    self.grid_repository.save_order(buy_order)
                    new_orders_created += 1
                    
                    # Crear orden de venta
                    sell_order = self.exchange_service.create_order(
                        pair=pair,
                        side='sell',
                        amount=amount_sell_each,
                        price=sell_price,
                        order_type='limit'
                    )
                    self.grid_repository.save_order(sell_order)
                    new_orders_created += 1
                
                actions.append(f"Creadas {new_orders_created} nuevas órdenes de grid")
                
            except Exception as e:
                logger.error(f"❌ Error reinicializando grid: {e}")
                actions.append("Error reinicializando grid")
            
            logger.info(f"📈 Trailing up ejecutado para {pair}: {', '.join(actions)}")
            
            return {
                'cancelled_orders': cancelled_orders,
                'new_orders_created': new_orders_created,
                'new_base_price': float(current_price),
                'actions': actions
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trailing up para {config.pair}: {e}")
            return {
                'error': str(e),
                'actions': []
            } 