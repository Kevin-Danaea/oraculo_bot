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
        
        Args:
            config: Configuración del bot
            current_price: Precio actual del par
            
        Returns:
            Lista de órdenes creadas
        """
        logger.info(f"🏗️ Creando grilla inicial para {config.pair} a precio ${current_price}")
        
        try:
            initial_orders = []
            
            # 1. Calcular niveles de grilla
            grid_levels = self.grid_calculator.calculate_grid_levels(current_price, config)
            
            # 2. Calcular cantidad por orden
            order_amount = self.grid_calculator.calculate_order_amount(
                config.total_capital, 
                config.grid_levels, 
                current_price
            )
            
            # 3. Crear órdenes de compra por debajo del precio actual
            buy_levels = [level for level in grid_levels if level < current_price]
            for price in buy_levels[:5]:  # Limitar a 5 niveles iniciales
                try:
                    order_value = price * order_amount
                    if order_value >= Decimal(MIN_ORDER_VALUE_USDT):
                        order = self.exchange_service.create_order(
                            pair=config.pair,
                            side='buy',
                            amount=order_amount,
                            price=price,
                            order_type='limit'
                        )
                        saved_order = self.grid_repository.save_order(order)
                        initial_orders.append(saved_order)
                        logger.info(f"✅ Orden de compra inicial: {order_amount} {config.pair} a ${price}")
                        
                except Exception as e:
                    logger.error(f"❌ Error creando orden de compra a ${price}: {e}")
                    continue
            
            # 4. Crear órdenes de venta por encima del precio actual
            sell_levels = [level for level in grid_levels if level > current_price]
            for price in sell_levels[:3]:  # Limitar a 3 niveles iniciales
                try:
                    # Verificar balance disponible
                    base_currency = config.pair.split('/')[0]
                    balance = self.exchange_service.get_balance(base_currency)
                    
                    if balance >= order_amount:
                        order_value = price * order_amount
                        if order_value >= Decimal(MIN_ORDER_VALUE_USDT):
                            order = self.exchange_service.create_order(
                                pair=config.pair,
                                side='sell',
                                amount=order_amount,
                                price=price,
                                order_type='limit'
                            )
                            saved_order = self.grid_repository.save_order(order)
                            initial_orders.append(saved_order)
                            logger.info(f"✅ Orden de venta inicial: {order_amount} {config.pair} a ${price}")
                    else:
                        logger.warning(f"⚠️ Balance insuficiente para venta: {balance} < {order_amount}")
                        
                except Exception as e:
                    logger.error(f"❌ Error creando orden de venta a ${price}: {e}")
                    continue
            
            logger.info(f"✅ Grilla inicial creada: {len(initial_orders)} órdenes para {config.pair}")
            return initial_orders
            
        except Exception as e:
            logger.error(f"❌ Error creando grilla inicial para {config.pair}: {e}")
            return [] 