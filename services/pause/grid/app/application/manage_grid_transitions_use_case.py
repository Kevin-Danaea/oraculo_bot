"""
Caso de uso para manejar transiciones de estado de los bots de Grid Trading.
Se encarga de detectar cambios de estado y ejecutar las acciones correspondientes.
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder
from app.config import MIN_ORDER_VALUE_USDT
from shared.services.logging_config import get_logger
from app.infrastructure.notification_service import TelegramGridNotificationService
from .realtime_grid_monitor_use_case import RealTimeGridMonitorUseCase

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
        grid_calculator: GridCalculator,
        realtime_monitor: Optional[RealTimeGridMonitorUseCase] = None
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.grid_calculator = grid_calculator
        self.realtime_monitor = realtime_monitor
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
                    'initializations': 0,
                    'message': 'No hay configuraciones para evaluar'
                }
            
            logger.info(f"📊 Evaluando transiciones para {len(configs_with_decisions)} configuraciones")
            
            # 2. Procesar cada configuración y detectar transiciones
            transitions = []
            activations = 0
            pauses = 0
            initializations = 0
            
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
                        elif transition_result['action'] == 'initialize_orders':
                            initializations += 1
                            
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
            logger.info(f"📈 Activaciones: {activations}, 📉 Pausas: {pauses}, 🔧 Inicializaciones: {initializations}")
            
            return {
                'success': True,
                'transitions_processed': len(transitions),
                'successful_transitions': successful_transitions,
                'activations': activations,
                'pauses': pauses,
                'initializations': initializations,
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
        
        # Si no hay cambio real, verificar si hay órdenes activas para inicialización
        if transition_type == 'no_change':
            # Consultar órdenes activas directamente en el exchange
            exchange_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            
            # 🔍 DIAGNÓSTICO: Logging detallado para entender por qué no encuentra órdenes
            logger.debug(f"🔍 DIAGNÓSTICO {config.pair}:")
            logger.debug(f"   - Bot is_running: {config.is_running}")
            logger.debug(f"   - Current decision: {current_decision}")
            logger.debug(f"   - Exchange orders found: {len(exchange_orders)}")
            
            if exchange_orders:
                logger.debug(f"   - Exchange order IDs: {[o.get('exchange_order_id', 'N/A') for o in exchange_orders[:5]]}")
            else:
                logger.info(f"   - ⚠️ NO SE ENCONTRARON ÓRDENES EN EL EXCHANGE")
                
                # 🔍 DETECTAR SI ES PRIMERA INICIALIZACIÓN
                is_first_initialization = not config.last_decision or config.last_decision == "PAUSAR_GRID"
                
                if is_first_initialization:
                    logger.info(f"   - 🟢 Primera inicialización detectada para {config.pair}, no se ejecuta retry.")
                else:
                    logger.info(f"   - 🔄 Bot ya estuvo activo antes, ejecutando retry robusto...")
                    
                    # 🔄 RETRY ROBUSTO: Solo para bots que ya estuvieron activos
                    import time
                    max_retries = 3
                    retry_delays = [2, 5, 10]  # segundos
                    
                    for retry_attempt in range(max_retries):
                        logger.info(f"   - 🔄 Reintentando consulta de órdenes (intento {retry_attempt + 1}/{max_retries}) después de {retry_delays[retry_attempt]}s...")
                        time.sleep(retry_delays[retry_attempt])
                        
                        exchange_orders_retry = self.exchange_service.get_active_orders_from_exchange(config.pair)
                        logger.info(f"   - Exchange orders after retry {retry_attempt + 1}: {len(exchange_orders_retry)}")
                        
                        if exchange_orders_retry:
                            logger.info(f"   - ✅ RETRY EXITOSO: Encontradas {len(exchange_orders_retry)} órdenes en intento {retry_attempt + 1}")
                            exchange_orders = exchange_orders_retry
                            break
                        else:
                            logger.warning(f"   - ❌ RETRY {retry_attempt + 1} FALLIDO: Aún no se encuentran órdenes")
                    
                    if not exchange_orders:
                        logger.warning(f"   - 🚨 TODOS LOS RETRIES FALLARON: No se encontraron órdenes después de {max_retries} intentos")
            
            # 🔒 LÓGICA SIMPLIFICADA: Solo considerar exchange como fuente de verdad
            has_orders_in_exchange = len(exchange_orders) > 0
            
            if (config.is_running and 
                current_decision == "OPERAR_GRID" and 
                not has_orders_in_exchange):
                
                # Determinar el tipo de inicialización para el logging
                is_first_initialization = not config.last_decision or config.last_decision == "PAUSAR_GRID"
                init_type = "primera inicialización" if is_first_initialization else "reinicialización después de retry"
                
                logger.info(f"🔧 Bot {config.pair} está activo pero sin órdenes en exchange - {init_type}")
                transition_type = 'initialize_orders'
            else:
                logger.debug(f"ℹ️ Sin cambios para {config.pair} - órdenes encontradas en exchange: {has_orders_in_exchange}")
                return {
                    'pair': config.pair,
                    'transition_detected': False,
                    'action': 'no_change',
                    'success': True,
                    'details': 'Sin cambios en la decisión.'
                }
        
        try:
            if transition_type == 'activate':
                # Solo crear órdenes iniciales si no existen en el exchange
                logger.info(f"🔧 Activando bot {config.pair} y no hay órdenes en el exchange - creando grilla inicial")
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
            elif transition_type == 'initialize_orders':
                result = self._handle_initialize_orders(config, current_decision)
                return {
                    'pair': config.pair,
                    'transition_detected': True,
                    'action': 'initialize_orders',
                    'success': result['success'],
                    'details': result
                }
            else:
                return {
                    'pair': config.pair,
                    'transition_detected': False,
                    'action': 'no_change',
                    'success': True,
                    'details': 'Sin cambios en la decisión.'
                }
                
        except Exception as e:
            logger.error(f"❌ Error procesando transición para {config.pair}: {e}")
            return {
                'pair': config.pair,
                'transition_detected': False,
                'action': 'error',
                'success': False,
                'error': str(e)
            }

    def _detect_transition_type(self, current_decision: str, previous_state: str) -> str:
        """
        Detecta el tipo de transición basado en el estado actual y anterior.
        
        Returns:
            'activate', 'pause', 'initialize_orders', o 'no_change'
        """
        # Normalizar estados para comparación
        is_currently_active = current_decision == "OPERAR_GRID"
        was_previously_active = previous_state == "OPERAR_GRID"
        
        # Si no hay cambio real en la decisión, no hay transición
        if current_decision == previous_state:
            return 'no_change'
        
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
            existing_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            
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
            
            # 6. Enviar notificación detallada con resumen de activación
            if 'initial_orders' in locals() and initial_orders:
                buy_orders = len([o for o in initial_orders if o.side == 'buy'])
                sell_orders = len([o for o in initial_orders if o.side == 'sell'])
                
                # Obtener información del capital usado
                bot_balance = self.exchange_service.get_bot_allocated_balance(config)
                allocated_capital = bot_balance['allocated_capital']
                
                # Calcular capital utilizado (aproximado)
                capital_used = sum(o.price * o.amount for o in initial_orders if o.side == 'buy')
                
                activation_summary = (
                    f"🚀 <b>BOT ACTIVADO - {config.pair}</b>\n\n"
                    f"💰 <b>Capital asignado:</b> ${allocated_capital:.2f} USDT\n"
                    f"💵 <b>Capital utilizado:</b> ${capital_used:.2f} USDT\n"
                    f"📊 <b>Órdenes creadas:</b> {len(initial_orders)} total\n"
                    f"   📈 Compras: {buy_orders} órdenes\n"
                    f"   📉 Ventas: {sell_orders} órdenes\n"
                    f"🎯 <b>Precio actual:</b> ${current_price:.4f}\n"
                    f"⚙️ <b>Niveles de grilla:</b> {config.grid_levels}\n"
                    f"📅 <b>Activado:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
                )
                
                # Enviar notificación detallada
                notification_service = TelegramGridNotificationService()
                notification_service.telegram_service.send_message(activation_summary)
                logger.info(f"📱 Notificación detallada enviada para activación de {config.pair}")
            
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
        Maneja la pausa de un bot (CANCELA órdenes y preserva activos).
        
        Args:
            config: Configuración del bot
            decision: Decisión actual
            
        Returns:
            Dict con el resultado de la pausa
        """
        logger.info(f"⏸️ PAUSANDO bot para {config.pair} (cancelando órdenes)")
        
        try:
            actions = []
            
            # 1. Obtener órdenes activas y balance actual
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            
            # 2. CANCELAR todas las órdenes activas
            cancelled_orders = 0
            if active_orders:
                logger.info(f"🚫 Cancelando {len(active_orders)} órdenes activas para {config.pair}")
                cancelled_orders = self.exchange_service.cancel_all_orders_for_pair(config.pair)
                actions.append(f"Canceladas {cancelled_orders} órdenes activas")
            else:
                actions.append("No había órdenes activas para cancelar")
            
            # 3. Actualizar estado en BD (marcar como no running y PAUSAR_GRID)
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
            
            # 4. Calcular estado preservado (solo activos, no órdenes)
            base_currency = config.pair.split('/')[0]
            assets_in_usdt = bot_balance['base_value_usdt']
            usdt_balance = bot_balance['quote_value_usdt']
            total_value = bot_balance['total_value_usdt']
            
            # 5. Notificar pausa con estado preservado
            pause_message = (
                f"⏸️ <b>BOT PAUSADO - {config.pair}</b>\n\n"
                f"💰 <b>Estado preservado:</b>\n"
                f"  🪙 {base_currency}: ${assets_in_usdt:.2f} USDT\n"
                f"  💵 USDT: ${usdt_balance:.2f}\n"
                f"  💎 Total: ${total_value:.2f}\n"
                f"🚫 <b>Órdenes canceladas:</b> {cancelled_orders}\n"
                f"📊 <b>Capital asignado:</b> ${config.total_capital:.2f}\n\n"
                f"ℹ️ <b>Nota:</b> Las órdenes fueron canceladas pero los activos se preservan.\n"
                f"🔄 <b>Reanudación:</b> Al activar, se crearán nuevas órdenes con los activos disponibles."
            )
            
            # Enviar notificación detallada
            self.notification_service.send_bot_status_notification(config.pair, "PAUSADO", "Decisión del Cerebro")
            
            # 6. Resetear estado de inicialización para el bot pausado
            if self.realtime_monitor:
                self.realtime_monitor.reset_initialization_status(config.pair)
                logger.info(f"🔄 Estado de inicialización reseteado para bot pausado {config.pair}")
            
            logger.info(f"✅ Bot {config.pair} pausado exitosamente (órdenes canceladas)")
            
            return {
                'success': True,
                'actions': actions,
                'orders_cancelled': cancelled_orders,
                'assets_preserved': float(assets_in_usdt),
                'usdt_preserved': float(usdt_balance),
                'total_preserved': float(total_value)
            }
            
        except Exception as e:
            logger.error(f"❌ Error pausando bot {config.pair}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_initialize_orders(self, config: GridConfig, decision: str) -> Dict[str, Any]:
        """
        Maneja la creación de órdenes iniciales para un bot activo sin órdenes.
        Se ejecuta cuando un bot está activo pero no tiene órdenes (ej: después de reinicio).
        
        Args:
            config: Configuración del bot
            decision: Decisión actual
            
        Returns:
            Dict con el resultado de la inicialización
        """
        logger.info(f"🔧 INICIALIZANDO órdenes para bot activo {config.pair}")
        
        try:
            actions = []
            
            # 1. Verificar que el bot esté marcado como activo
            if not config.is_running:
                logger.warning(f"⚠️ Bot {config.pair} no está marcado como running, actualizando estado")
                if config.id is not None:
                    self.grid_repository.update_config_status(
                        config.id, 
                        is_running=True, 
                        last_decision=decision
                    )
                    actions.append("Estado actualizado a activo")
            
            # 2. Obtener precio actual
            current_price = self.exchange_service.get_current_price(config.pair)
            logger.info(f"💰 Precio actual {config.pair}: ${current_price}")
            
            # 3. Verificar que no haya órdenes activas (doble verificación)
            existing_orders = self.grid_repository.get_active_orders(config.pair)
            if existing_orders:
                logger.warning(f"⚠️ Bot {config.pair} ya tiene {len(existing_orders)} órdenes activas")
                actions.append(f"Bot ya tiene {len(existing_orders)} órdenes activas")
                return {
                    'success': True,
                    'actions': actions,
                    'existing_orders': len(existing_orders),
                    'initial_orders': 0
                }
            
            # 4. Crear grilla inicial
            initial_orders = self._create_initial_grid(config, current_price)
            if initial_orders:
                actions.append(f"Grilla inicial creada: {len(initial_orders)} órdenes")
                logger.info(f"✅ Grilla inicial creada para {config.pair}: {len(initial_orders)} órdenes")
                
                # 5. Enviar notificación detallada
                buy_orders = len([o for o in initial_orders if o.side == 'buy'])
                sell_orders = len([o for o in initial_orders if o.side == 'sell'])
                
                # Obtener información del capital usado
                bot_balance = self.exchange_service.get_bot_allocated_balance(config)
                allocated_capital = bot_balance['allocated_capital']
                
                # Calcular capital utilizado (aproximado)
                capital_used = sum(o.price * o.amount for o in initial_orders if o.side == 'buy')
                
                initialization_summary = (
                    f"🔧 <b>ÓRDENES INICIALIZADAS - {config.pair}</b>\n\n"
                    f"💰 <b>Capital asignado:</b> ${allocated_capital:.2f} USDT\n"
                    f"💵 <b>Capital utilizado:</b> ${capital_used:.2f} USDT\n"
                    f"📊 <b>Órdenes creadas:</b> {len(initial_orders)} total\n"
                    f"   📈 Compras: {buy_orders} órdenes\n"
                    f"   📉 Ventas: {sell_orders} órdenes\n"
                    f"🎯 <b>Precio actual:</b> ${current_price:.4f}\n"
                    f"⚙️ <b>Niveles de grilla:</b> {config.grid_levels}\n"
                    f"📅 <b>Inicializado:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
                )
                
                # Enviar notificación detallada
                notification_service = TelegramGridNotificationService()
                notification_service.telegram_service.send_message(initialization_summary)
                logger.info(f"📱 Notificación detallada enviada para inicialización de {config.pair}")
                
            else:
                actions.append("No se pudieron crear órdenes iniciales")
                logger.warning(f"⚠️ No se pudieron crear órdenes iniciales para {config.pair}")
            
            logger.info(f"✅ Bot {config.pair} inicializado exitosamente")
            
            return {
                'success': True,
                'actions': actions,
                'current_price': float(current_price),
                'existing_orders': len(existing_orders),
                'initial_orders': len(initial_orders) if initial_orders else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error inicializando órdenes para bot {config.pair}: {e}")
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
            # 1) VERIFICAR Y LIMPIAR ÓRDENES EXISTENTES
            cancelled_existing = self._verify_and_cleanup_orders_before_initialization(config)
            if cancelled_existing > 0:
                logger.info(f"🧹 Bot {config.pair}: {cancelled_existing} órdenes existentes canceladas antes de crear grilla inicial")
            
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
                
                # ESPERAR A QUE EL ACTIVO ESTÉ DISPONIBLE PARA VENTA
                logger.info(f"⏳ Bot {pair}: Esperando a que {filled_amount_net} {base_currency} esté disponible para venta...")
                max_retries = 10
                retry_delay = 2  # segundos
                
                for retry in range(max_retries):
                    try:
                        # Verificar si el activo está disponible
                        sell_check = self.exchange_service.can_bot_use_capital(config, filled_amount_net, 'sell')
                        if sell_check['can_use']:
                            logger.info(f"✅ Bot {pair}: {filled_amount_net} {base_currency} disponible para venta (intento {retry + 1})")
                            break
                        else:
                            logger.info(f"⏳ Bot {pair}: {base_currency} aún no disponible. Disponible: {sell_check['available_balance']}. Reintentando en {retry_delay}s...")
                            import time
                            time.sleep(retry_delay)
                    except Exception as e:
                        logger.warning(f"⚠️ Bot {pair}: Error verificando disponibilidad de {base_currency}: {e}")
                        if retry < max_retries - 1:
                            import time
                            time.sleep(retry_delay)
                else:
                    logger.warning(f"⚠️ Bot {pair}: {base_currency} no disponible después de {max_retries} intentos. Continuando solo con órdenes de compra.")
                    filled_amount_net = Decimal('0')  # No crear órdenes de venta
                
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
            # Usar todo el capital disponible para las órdenes de compra (no solo half_capital)
            total_capital_for_orders = actual_capital - half_capital  # El otro 50% para órdenes de compra
            
            amount_per_order = self.grid_calculator.calculate_order_amount(
                total_capital=float(total_capital_for_orders),
                grid_levels=len(lower_levels),
                current_price=current_price,
            )
            
            logger.info(f"💰 Bot {pair}: Capital para órdenes de compra: ${total_capital_for_orders:.2f}")
            logger.info(f"📊 Bot {pair}: Cantidad por orden de compra: {amount_per_order} {base_currency}")

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
                    # 🔒 CONTROL DE LÍMITE: Verificar que no excedemos grid_levels
                    if len(initial_orders) >= config.grid_levels:
                        logger.warning(f"🚦 Bot {pair}: Límite de órdenes alcanzado ({len(initial_orders)}/{config.grid_levels}). Deteniendo creación de órdenes.")
                        break
                    
                    logger.info(f"🔧 Bot {pair}: Procesando nivel {idx+1}/{len(lower_levels)} - Compra: ${buy_price:.4f}, Venta: ${sell_price:.4f}")
                    
                    # Verificar que no excedemos el capital asignado al bot
                    order_value = buy_price * amount_per_order
                    if capital_used + order_value > total_capital_for_orders:
                        logger.warning(f"⚠️ Bot {pair}: Límite de capital asignado alcanzado en nivel {idx}. Capital usado: ${capital_used:.2f}")
                        break
                    
                    # Verificar que el bot puede usar este capital
                    capital_check = self.exchange_service.can_bot_use_capital(config, order_value, 'buy')
                    if not capital_check['can_use']:
                        logger.warning(f"⚠️ Bot {pair}: No puede usar ${order_value} USDT para orden de compra. Disponible: ${capital_check['available_balance']}")
                        break
                    
                    # Validar que la orden cumple con el mínimo después de comisiones
                    order_validation = self.exchange_service.validate_order_after_fees(
                        pair=pair,
                        side='buy',
                        amount=amount_per_order,
                        price=buy_price
                    )
                    
                    if not order_validation['valid']:
                        logger.warning(f"⚠️ Bot {pair}: Orden de compra no cumple mínimo después de comisiones: ${order_validation['net_value']:.2f} < ${order_validation['min_required']}")
                        # Intentar ajustar la cantidad para cumplir con el mínimo
                        min_amount = order_validation['min_required'] / buy_price
                        if min_amount > amount_per_order:
                            logger.info(f"🔧 Bot {pair}: Ajustando cantidad de compra de {amount_per_order} a {min_amount:.6f} {base_currency}")
                            amount_per_order = min_amount.quantize(Decimal('0.000001'))
                            order_value = buy_price * amount_per_order
                            
                            # Verificar nuevamente que no excedemos el capital
                            if capital_used + order_value > total_capital_for_orders:
                                logger.warning(f"⚠️ Bot {pair}: Ajuste de cantidad excede capital asignado")
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
                            # Validar que la orden de venta cumple con el mínimo después de comisiones
                            sell_validation = self.exchange_service.validate_order_after_fees(
                                pair=pair,
                                side='sell',
                                amount=amount_sell_each,
                                price=sell_price
                            )
                            
                            if not sell_validation['valid']:
                                logger.warning(f"⚠️ Bot {pair}: Orden de venta no cumple mínimo después de comisiones: ${sell_validation['net_value']:.2f} < ${sell_validation['min_required']}")
                                # Intentar ajustar la cantidad para cumplir con el mínimo
                                min_amount = sell_validation['min_required'] / sell_price
                                if min_amount > amount_sell_each:
                                    logger.info(f"🔧 Bot {pair}: Ajustando cantidad de venta de {amount_sell_each} a {min_amount:.6f} {base_currency}")
                                    amount_sell_each = min_amount.quantize(Decimal('0.000001'))
                            
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
            logger.info(f"💰 Bot {pair}: Capital utilizado ${capital_used:.2f} de ${total_capital_for_orders:.2f} asignado")
            logger.info(f"📊 Bot {pair}: Total de órdenes creadas: {len(initial_orders)}")
            
            return initial_orders
            
        except Exception as e:
            logger.error(f"❌ Error creando grilla inicial para bot {config.pair}: {e}")
            return [] 

    def _verify_and_cleanup_orders_before_initialization(self, config: GridConfig) -> int:
        """
        Verifica y limpia órdenes existentes antes de crear la grilla inicial.
        
        Args:
            config: Configuración del bot
            
        Returns:
            int: Número de órdenes canceladas
        """
        try:
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            if not active_orders:
                return 0
            
            logger.info(f"🧹 Bot {config.pair}: Limpiando {len(active_orders)} órdenes existentes antes de inicialización")
            
            # Cancelar todas las órdenes existentes
            cancelled_count = self.exchange_service.cancel_all_orders_for_pair(config.pair)
            
            if cancelled_count > 0:
                logger.info(f"✅ Bot {config.pair}: {cancelled_count} órdenes canceladas antes de inicialización")
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"❌ Error limpiando órdenes antes de inicialización para {config.pair}: {e}")
            return 0

# Ejemplo de uso del flujo corregido:
"""
# Ejemplo de uso del flujo de pausa corregido:

# 1. El cerebro detecta cambios y envía decisión PAUSAR_GRID
# 2. El caso de uso detecta la transición: OPERAR_GRID → PAUSAR_GRID
# 3. Se ejecuta _handle_pause que:
#    - Cancela todas las órdenes activas del exchange
#    - Actualiza is_running=False en la BD
#    - Actualiza last_decision=PAUSAR_GRID en la BD
#    - Resetea el estado de inicialización
#    - Envía notificación de pausa
# 4. El bot queda completamente pausado (no genera órdenes complementarias)
# 5. Al reactivar, se ejecuta _handle_activation que:
#    - Actualiza is_running=True en la BD
#    - Crea nuevas órdenes con los activos disponibles
#    - Envía notificación de activación

# Flujo de notificaciones:
# - Solo se notifica cuando hay cambio real de estado
# - No se repiten notificaciones para el mismo estado
# - Se incluye información detallada de órdenes canceladas y activos preservados
""" 