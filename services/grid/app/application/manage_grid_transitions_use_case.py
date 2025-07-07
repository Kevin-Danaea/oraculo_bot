"""
Caso de uso para manejar transiciones de estado de los bots de Grid Trading.
Se encarga de detectar cambios de estado y ejecutar las acciones correspondientes.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder
from app.config import MIN_ORDER_VALUE_USDT
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class ManageGridTransitionsUseCase:
    """
    Caso de uso que maneja las transiciones de estado de los bots de Grid Trading.
    
    Responsabilidades:
    - Detectar cambios de estado (pausado ↔ activo)
    - Cancelar órdenes al pausar
    - Crear grilla inicial al activar
    - Actualizar estado en BD
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
        logger.info("✅ ManageGridTransitionsUseCase inicializado.")

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta la detección y manejo de transiciones de estado.
        
        Returns:
            Dict con el resultado de las transiciones procesadas
        """
        logger.info("🔄 ========== DETECTANDO TRANSICIONES DE ESTADO ==========")
        
        try:
            # 1. Obtener todas las configuraciones con sus decisiones actuales
            configs_with_decisions = self.grid_repository.get_configs_with_decisions()
            
            if not configs_with_decisions:
                logger.info("ℹ️ No hay configuraciones para evaluar transiciones")
                return {
                    'success': True,
                    'transitions_processed': 0,
                    'activations': 0,
                    'pauses': 0,
                    'message': 'No hay configuraciones para evaluar'
                }
            
            logger.info(f"📊 Evaluando transiciones para {len(configs_with_decisions)} configuraciones")
            
            # 2. Procesar cada configuración y detectar transiciones
            transitions = []
            activations = 0
            pauses = 0
            
            for config, current_decision, previous_state in configs_with_decisions:
                try:
                    transition_result = self._process_config_transition(
                        config, current_decision, previous_state
                    )
                    
                    if transition_result['transition_detected']:
                        transitions.append(transition_result)
                        
                        if transition_result['action'] == 'activation':
                            activations += 1
                        elif transition_result['action'] == 'pause':
                            pauses += 1
                            
                except Exception as e:
                    logger.error(f"❌ Error procesando transición para {config.pair}: {e}")
                    transitions.append({
                        'pair': config.pair,
                        'success': False,
                        'error': str(e)
                    })
            
            # 3. Generar resumen
            successful_transitions = sum(1 for t in transitions if t.get('success', False))
            
            logger.info(f"✅ Transiciones completadas: {successful_transitions}/{len(transitions)} exitosas")
            logger.info(f"📈 Activaciones: {activations}, 📉 Pausas: {pauses}")
            
            return {
                'success': True,
                'transitions_processed': len(transitions),
                'successful_transitions': successful_transitions,
                'activations': activations,
                'pauses': pauses,
                'transitions': transitions
            }
            
        except Exception as e:
            logger.error(f"❌ Error en gestión de transiciones: {e}")
            self.notification_service.send_error_notification("Grid Transitions Manager", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    def _process_config_transition(
        self, 
        config: GridConfig, 
        current_decision: str, 
        previous_state: str
    ) -> Dict[str, Any]:
        """
        Procesa la transición de estado para una configuración específica.
        
        Args:
            config: Configuración del bot
            current_decision: Decisión actual del Cerebro
            previous_state: Estado anterior del bot
            
        Returns:
            Dict con el resultado de la transición
        """
        logger.info(f"🔍 Evaluando transición {config.pair}: {previous_state} → {current_decision}")
        
        # Detectar tipo de transición
        transition_type = self._detect_transition_type(current_decision, previous_state)
        
        if transition_type == 'no_change':
            logger.debug(f"ℹ️ Sin cambios para {config.pair}")
            return {
                'pair': config.pair,
                'transition_detected': False,
                'action': 'no_change',
                'success': True
            }
        
        try:
            if transition_type == 'activate':
                result = self._handle_activation(config, current_decision)
                return {
                    'pair': config.pair,
                    'transition_detected': True,
                    'action': 'activation',
                    'success': result['success'],
                    'details': result
                }
                
            elif transition_type == 'pause':
                result = self._handle_pause(config, current_decision)
                return {
                    'pair': config.pair,
                    'transition_detected': True,
                    'action': 'pause',
                    'success': result['success'],
                    'details': result
                }
                
        except Exception as e:
            logger.error(f"❌ Error en transición {transition_type} para {config.pair}: {e}")
            return {
                'pair': config.pair,
                'transition_detected': True,
                'action': transition_type,
                'success': False,
                'error': str(e)
            }
        
        return {
            'pair': config.pair,
            'transition_detected': False,
            'action': 'unknown',
            'success': False
        }

    def _detect_transition_type(self, current_decision: str, previous_state: str) -> str:
        """
        Detecta el tipo de transición basado en el estado actual y anterior.
        
        Returns:
            'activate', 'pause', o 'no_change'
        """
        # Normalizar estados para comparación
        is_currently_active = current_decision == "OPERAR_GRID"
        was_previously_active = previous_state == "OPERAR_GRID"
        
        if not was_previously_active and is_currently_active:
            return 'activate'  # pausado → activo
        elif was_previously_active and not is_currently_active:
            return 'pause'     # activo → pausado
        else:
            return 'no_change' # sin cambios
    
    def _handle_activation(self, config: GridConfig, decision: str) -> Dict[str, Any]:
        """
        Maneja la activación de un bot (crear grilla inicial).
        
        Args:
            config: Configuración del bot
            decision: Decisión actual
            
        Returns:
            Dict con el resultado de la activación
        """
        logger.info(f"🚀 ACTIVANDO bot para {config.pair}")
        
        try:
            actions = []
            
            # 1. Actualizar estado en BD
            if config.id is not None:
                self.grid_repository.update_config_status(
                    config.id, 
                    is_running=True, 
                    last_decision=decision
                )
                actions.append("Estado actualizado a activo")
            else:
                logger.error(f"❌ Config ID es None para {config.pair}")
                return {'success': False, 'error': 'Config ID es None'}
            
            # 2. Obtener precio actual
            current_price = self.exchange_service.get_current_price(config.pair)
            logger.info(f"💰 Precio actual {config.pair}: ${current_price}")
            
            # 3. Verificar si ya hay órdenes activas
            existing_orders = self.grid_repository.get_active_orders(config.pair)
            
            if not existing_orders:
                # 4. Crear grilla inicial si no hay órdenes
                initial_orders = self._create_initial_grid(config, current_price)
                if initial_orders:
                    actions.append(f"Grilla inicial creada: {len(initial_orders)} órdenes")
                    logger.info(f"✅ Grilla inicial creada para {config.pair}: {len(initial_orders)} órdenes")
                else:
                    actions.append("No se pudieron crear órdenes iniciales")
                    logger.warning(f"⚠️ No se pudieron crear órdenes iniciales para {config.pair}")
            else:
                actions.append(f"Reactivado con {len(existing_orders)} órdenes existentes")
                logger.info(f"🔄 Bot reactivado con órdenes existentes: {len(existing_orders)}")
            
            # 5. Notificar activación
            self.notification_service.send_bot_status_notification(config.pair, "ACTIVADO", "Decisión del Cerebro")
            
            logger.info(f"✅ Bot {config.pair} activado exitosamente")
            
            return {
                'success': True,
                'actions': actions,
                'current_price': float(current_price),
                'existing_orders': len(existing_orders),
                'initial_orders': len(initial_orders) if 'initial_orders' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error activando bot {config.pair}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_pause(self, config: GridConfig, decision: str) -> Dict[str, Any]:
        """
        Maneja la pausa de un bot (cancelar órdenes activas).
        
        Args:
            config: Configuración del bot
            decision: Decisión actual
            
        Returns:
            Dict con el resultado de la pausa
        """
        logger.info(f"⏸️ PAUSANDO bot para {config.pair}")
        
        try:
            actions = []
            
            # 1. Obtener órdenes activas antes de cancelar
            active_orders = self.grid_repository.get_active_orders(config.pair)
            
            # 2. Cancelar órdenes en el exchange
            cancelled_orders = 0
            if active_orders:
                for order in active_orders:
                    if order.exchange_order_id and order.status == 'open':
                        try:
                            success = self.exchange_service.cancel_order(config.pair, order.exchange_order_id)
                            if success:
                                cancelled_orders += 1
                        except Exception as e:
                            logger.error(f"❌ Error cancelando orden {order.exchange_order_id}: {e}")
                
                actions.append(f"Canceladas {cancelled_orders}/{len(active_orders)} órdenes del exchange")
            
            # 3. Cancelar órdenes en BD
            cancelled_in_db = self.grid_repository.cancel_all_orders_for_pair(config.pair)
            if cancelled_in_db > 0:
                actions.append(f"Canceladas {cancelled_in_db} órdenes en BD")
            
            # 4. Actualizar estado en BD
            if config.id is not None:
                self.grid_repository.update_config_status(
                    config.id, 
                    is_running=False, 
                    last_decision=decision
                )
                actions.append("Estado actualizado a pausado")
            else:
                logger.error(f"❌ Config ID es None para {config.pair}")
                return {'success': False, 'error': 'Config ID es None'}
            
            # 5. Notificar pausa
            self.notification_service.send_bot_status_notification(config.pair, "PAUSADO", "Decisión del Cerebro")
            
            logger.info(f"✅ Bot {config.pair} pausado exitosamente")
            
            return {
                'success': True,
                'actions': actions,
                'orders_in_exchange': len(active_orders),
                'cancelled_in_exchange': cancelled_orders,
                'cancelled_in_db': cancelled_in_db
            }
            
        except Exception as e:
            logger.error(f"❌ Error pausando bot {config.pair}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _create_initial_grid(self, config: GridConfig, current_price: Decimal) -> List[GridOrder]:
        """
        Crea la grilla inicial de órdenes para un bot recién activado.
        RESPETA AISLAMIENTO DE CAPITAL: Cada bot solo usa su capital asignado.
        
        Args:
            config: Configuración del bot
            current_price: Precio actual del par
            
        Returns:
            Lista de órdenes creadas
        """
        logger.info(f"🏗️ Creando grilla inicial para {config.pair} a precio ${current_price}")
        
        try:
            initial_orders = []
            pair = config.pair
            configured_capital = Decimal(config.total_capital)
            
            # 1) OBTENER BALANCE ASIGNADO AL BOT ESPECÍFICO
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            allocated_capital = bot_balance['allocated_capital']
            total_available = bot_balance['total_value_usdt']
            
            logger.info(f"🔒 Bot {pair}: Capital asignado ${allocated_capital:.2f}, Disponible en cuenta ${total_available:.2f}")
            
            # 2) VERIFICAR QUE EL BOT PUEDA OPERAR CON SU CAPITAL ASIGNADO
            if total_available < allocated_capital:
                logger.warning(f"⚠️ Bot {pair}: Capital disponible ${total_available:.2f} < Capital asignado ${allocated_capital:.2f}")
                logger.info(f"🔧 Ajustando capital a disponible: ${total_available:.2f}")
                actual_capital = total_available
            else:
                actual_capital = allocated_capital
                logger.info(f"✅ Bot {pair}: Capital verificado ${actual_capital:.2f} (aislamiento respetado)")
            
            # Usar 50% del capital asignado al bot
            half_capital = actual_capital / Decimal(2)
            
            # 3) COMPRAR 50% DEL CAPITAL ASIGNADO AL MERCADO
            base_currency = pair.split('/')[0]
            amount_market = (half_capital / current_price).quantize(Decimal('0.000001'))
            
            logger.info(f"🏁 Bot {pair}: Comprando {amount_market} {base_currency} (~${half_capital}) al mercado")
            
            try:
                # Verificar que el bot puede usar este capital
                capital_check = self.exchange_service.can_bot_use_capital(config, half_capital, 'buy')
                if not capital_check['can_use']:
                    logger.error(f"❌ Bot {pair} no puede usar ${half_capital} USDT. Disponible: ${capital_check['available_balance']}")
                    return []
                
                market_order = self.exchange_service.create_order(
                    pair=pair,
                    side='buy',
                    amount=amount_market,
                    price=current_price,  # ignorado por market
                    order_type='market',
                )
                
                # Obtener cantidad real llenada
                if market_order.exchange_order_id:
                    status = self.exchange_service.get_order_status(pair, market_order.exchange_order_id)
                else:
                    status = {'filled': amount_market}
                
                filled_amount_gross = Decimal(str(status.get('filled', amount_market)))
                
                # 4) CALCULAR CANTIDAD NETA DESPUÉS DE COMISIONES
                filled_amount_net = self.exchange_service.calculate_net_amount_after_fees(
                    gross_amount=filled_amount_gross,
                    price=current_price,
                    side='buy',
                    pair=pair
                )
                
                logger.info(f"✅ Bot {pair}: Compra completada {filled_amount_gross} → {filled_amount_net} {base_currency} (después de comisiones)")
                
            except Exception as e:
                logger.error(f"❌ Error en compra de mercado para bot {pair}: {e}")
                return []

            # 5) CALCULAR NIVELES DE GRILLA
            grid_levels = self.grid_calculator.calculate_grid_levels(current_price, config)
            if len(grid_levels) != config.grid_levels:
                logger.warning(f"⚠️ Bot {pair}: Número de niveles calculado no coincide con la config")

            # Dividir niveles
            lower_levels = [p for p in grid_levels if p < current_price]
            upper_levels = [p for p in grid_levels if p > current_price]

            # Asegurar igualdad de listas
            min_len = min(len(lower_levels), len(upper_levels))
            lower_levels = lower_levels[-min_len:]
            upper_levels = upper_levels[:min_len]

            # 6) CALCULAR CANTIDADES POR ORDEN
            amount_per_order = self.grid_calculator.calculate_order_amount(
                total_capital=float(half_capital),
                grid_levels=len(lower_levels),
                current_price=current_price,
            )

            # 7) CREAR ÓRDENES INICIALES CON AISLAMIENTO DE CAPITAL
            # 7a) Órdenes de venta usando filled_amount_net distribuido
            if len(upper_levels) > 0:
                amount_sell_each = (filled_amount_net / Decimal(len(upper_levels))).quantize(Decimal('0.000001'))
                logger.info(f"📊 Bot {pair}: Creando {len(upper_levels)} órdenes de venta con {amount_sell_each} {base_currency} cada una")
            else:
                amount_sell_each = Decimal('0')
                logger.warning(f"⚠️ Bot {pair}: No hay niveles superiores para órdenes de venta")

            orders_created = 0
            capital_used = Decimal('0')
            buy_orders_created = 0
            sell_orders_created = 0

            logger.info(f"🏗️ Bot {pair}: Iniciando creación de grilla con {len(lower_levels)} niveles de compra y {len(upper_levels)} niveles de venta")

            for idx, (buy_price, sell_price) in enumerate(zip(lower_levels, upper_levels)):
                try:
                    logger.info(f"🔧 Bot {pair}: Procesando nivel {idx+1}/{len(lower_levels)} - Compra: ${buy_price:.4f}, Venta: ${sell_price:.4f}")
                    
                    # Verificar que no excedemos el capital asignado al bot
                    order_value = buy_price * amount_per_order
                    if capital_used + order_value > half_capital:
                        logger.warning(f"⚠️ Bot {pair}: Límite de capital asignado alcanzado en nivel {idx}. Capital usado: ${capital_used:.2f}")
                        break
                    
                    # Verificar que el bot puede usar este capital
                    capital_check = self.exchange_service.can_bot_use_capital(config, order_value, 'buy')
                    if not capital_check['can_use']:
                        logger.warning(f"⚠️ Bot {pair}: No puede usar ${order_value} USDT para orden de compra. Disponible: ${capital_check['available_balance']}")
                        break
                    
                    # Crear orden BUY
                    logger.info(f"📈 Bot {pair}: Creando orden de compra {amount_per_order} {base_currency} a ${buy_price:.4f}")
                    buy_order = self.exchange_service.create_order(
                        pair=pair,
                        side='buy',
                        amount=amount_per_order,
                        price=buy_price,
                        order_type='limit',
                    )
                    saved_buy_order = self.grid_repository.save_order(buy_order)
                    initial_orders.append(saved_buy_order)
                    capital_used += order_value
                    orders_created += 1
                    buy_orders_created += 1
                    logger.info(f"✅ Bot {pair}: Orden de compra creada exitosamente (ID: {saved_buy_order.exchange_order_id})")

                    # Crear orden SELL solo si tenemos cantidad suficiente
                    if amount_sell_each > Decimal('0'):
                        logger.info(f"📉 Bot {pair}: Verificando si puede vender {amount_sell_each} {base_currency}")
                        
                        # Verificar que el bot puede vender esta cantidad
                        sell_check = self.exchange_service.can_bot_use_capital(config, amount_sell_each, 'sell')
                        if sell_check['can_use']:
                            logger.info(f"📉 Bot {pair}: Creando orden de venta {amount_sell_each} {base_currency} a ${sell_price:.4f}")
                            sell_order = self.exchange_service.create_order(
                                pair=pair,
                                side='sell',
                                amount=amount_sell_each,
                                price=sell_price,
                                order_type='limit',
                            )
                            saved_sell_order = self.grid_repository.save_order(sell_order)
                            initial_orders.append(saved_sell_order)
                            orders_created += 1
                            sell_orders_created += 1
                            logger.info(f"✅ Bot {pair}: Orden de venta creada exitosamente (ID: {saved_sell_order.exchange_order_id})")
                        else:
                            logger.warning(f"⚠️ Bot {pair}: No puede vender {amount_sell_each} {base_currency}. Disponible: {sell_check['available_balance']}")
                    else:
                        logger.warning(f"⚠️ Bot {pair}: Cantidad de venta insuficiente ({amount_sell_each} {base_currency})")
                    
                except Exception as e:
                    logger.error(f"❌ Error creando órdenes para bot {pair} nivel {idx}: {e}")
                    continue

            logger.info(f"🎉 Bot {pair}: Grilla inicial completada - {buy_orders_created} órdenes de compra, {sell_orders_created} órdenes de venta")
            logger.info(f"💰 Bot {pair}: Capital utilizado ${capital_used:.2f} de ${half_capital:.2f} asignado")
            logger.info(f"📊 Bot {pair}: Total de órdenes creadas: {len(initial_orders)}")
            
            # Enviar notificación detallada con resumen de activación
            if initial_orders:
                activation_summary = (
                    f"🚀 <b>GRILLA INICIAL CREADA - {pair}</b>\n\n"
                    f"💰 <b>Capital asignado:</b> ${allocated_capital:.2f} USDT\n"
                    f"💵 <b>Capital utilizado:</b> ${capital_used:.2f} USDT\n"
                    f"📊 <b>Órdenes creadas:</b> {len(initial_orders)} total\n"
                    f"   📈 Compras: {buy_orders_created} órdenes\n"
                    f"   📉 Ventas: {sell_orders_created} órdenes\n"
                    f"🎯 <b>Precio actual:</b> ${current_price:.4f}\n"
                    f"⚙️ <b>Niveles de grilla:</b> {config.grid_levels}\n"
                    f"📅 <b>Creada:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
                )
                
                # Usar el servicio de notificación directamente
                from app.infrastructure.notification_service import TelegramGridNotificationService
                notification_service = TelegramGridNotificationService()
                notification_service.telegram_service.send_message(activation_summary)
                logger.info(f"📱 Notificación detallada enviada para grilla inicial de {pair}")
            
            return initial_orders
            
        except Exception as e:
            logger.error(f"❌ Error creando grilla inicial para bot {config.pair}: {e}")
            return [] 