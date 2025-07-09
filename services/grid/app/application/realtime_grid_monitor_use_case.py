"""
Caso de uso para monitoreo en tiempo real de órdenes de Grid Trading.
Optimizado para detectar fills inmediatamente y crear órdenes complementarias.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder, GridTrade, GridStep
from app.config import MIN_ORDER_VALUE_USDT, REALTIME_CACHE_EXPIRY_MINUTES
from shared.services.logging_config import get_logger
from .risk_management_use_case import RiskManagementUseCase

logger = get_logger(__name__)

class RealTimeGridMonitorUseCase:
    """
    Caso de uso especializado para monitoreo en tiempo real de Grid Trading.
    
    Responsabilidades:
    - Monitoreo continuo de órdenes activas (cada 5-10 segundos)
    - Detección inmediata de órdenes completadas (fills)
    - Creación automática de órdenes complementarias
    - Notificación de trades exitosos
    - Mantenimiento de grillas dinámicas
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
        
        # Inicializar gestión de riesgos
        self.risk_management = RiskManagementUseCase(
            grid_repository=grid_repository,
            exchange_service=exchange_service,
            notification_service=notification_service,
            grid_calculator=grid_calculator
        )
        
        # Cache para optimizar consultas
        self._last_check_time = {}
        self._active_configs_cache = []
        self._cache_expiry = None
        
        # Tracking de órdenes para detección de fills
        self._previous_active_orders = {}  # {pair: [orders]}
        self._last_fill_check = {}  # {pair: timestamp}
        
        # 🔒 NUEVO: Estado de inicialización por bot
        self._bot_initialization_status = {}  # {pair: {'initialized': bool, 'initial_orders_count': int, 'first_initialization_completed': bool}}
        self._initialization_check_interval = 30  # segundos entre verificaciones de inicialización
        
        # 📱 NUEVO: Acumulación de notificaciones de órdenes complementarias
        self._complementary_orders_notifications = []  # Lista de notificaciones acumuladas
        self._last_notification_cleanup = datetime.now()
        
        # 🎯 NUEVO: Sistema de tracking de trades completos
        self._pending_buys = {}  # {pair: {order_id: {'price': Decimal, 'amount': Decimal, 'timestamp': datetime}}}
        self._completed_trades = []  # Lista de trades completos para P&L
        
        logger.info("✅ RealTimeGridMonitorUseCase inicializado.")

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo de monitoreo en tiempo real.
        SOLO PARA BOTS COMPLETAMENTE INICIALIZADOS.
        
        Returns:
            Dict con el resultado del monitoreo en tiempo real
        """
        logger.debug("⚡ Ejecutando monitoreo en tiempo real...")
        
        try:
            # 1. Obtener configuraciones activas (con cache)
            active_configs = self._get_cached_active_configs()
            
            if not active_configs:
                logger.debug("ℹ️ No hay bots activos para monitoreo en tiempo real")
                return {
                    'success': True,
                    'monitored_bots': 0,
                    'fills_detected': 0,
                    'orders_created': 0,
                    'message': 'No hay bots activos'
                }
            
            # 2. Verificar estado de inicialización de cada bot
            ready_bots = []
            for config in active_configs:
                if self._is_bot_ready_for_realtime(config):
                    ready_bots.append(config)
                else:
                    logger.debug(f"⏳ Bot {config.pair} aún no está listo para monitoreo en tiempo real")
            
            if not ready_bots:
                logger.debug("⏳ No hay bots listos para monitoreo en tiempo real (esperando inicialización)")
                return {
                    'success': True,
                    'monitored_bots': 0,
                    'fills_detected': 0,
                    'orders_created': 0,
                    'message': 'Bots en proceso de inicialización'
                }
            
            # 3. Monitorear solo bots listos
            total_fills = 0
            total_new_orders = 0
            total_trades = 0
            risk_events = 0
            
            for config in ready_bots:
                try:
                    # Verificar eventos de riesgo primero
                    risk_result = self.risk_management.check_and_handle_risk_events(config)
                    if risk_result.get('events_handled'):
                        risk_events += len(risk_result['events_handled'])
                        logger.warning(f"🚨 Eventos de riesgo manejados para {config.pair}: {len(risk_result['events_handled'])} eventos")
                        continue  # Si hay eventos de riesgo, no continuar con monitoreo normal
                    
                    result = self._monitor_bot_realtime(config)
                    
                    total_fills += result.get('fills_detected', 0)
                    total_new_orders += result.get('new_orders_created', 0)
                    total_trades += result.get('trades_completed', 0)
                    
                except Exception as e:
                    logger.error(f"❌ Error en monitoreo tiempo real para {config.pair}: {e}")
                    continue
            
            # 4. Log resumen solo si hubo actividad
            if total_fills > 0 or total_new_orders > 0 or risk_events > 0:
                logger.info(f"⚡ RT Monitor: {len(ready_bots)} bots listos, {total_fills} fills, {total_new_orders} nuevas órdenes, {risk_events} eventos de riesgo")
            
            return {
                'success': True,
                'monitored_bots': len(ready_bots),
                'total_bots': len(active_configs),
                'fills_detected': total_fills,
                'orders_created': total_new_orders,
                'trades_completed': total_trades,
                'risk_events_handled': risk_events
            }
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo tiempo real: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_cached_active_configs(self) -> List[GridConfig]:
        """
        Obtiene configuraciones activas con cache para optimizar performance.
        Cache se renueva según REALTIME_CACHE_EXPIRY_MINUTES.
        """
        now = datetime.now()
        
        # Renovar cache si expiró o es la primera vez
        if self._cache_expiry is None or now > self._cache_expiry:
            self._active_configs_cache = self.grid_repository.get_active_configs()
            self._cache_expiry = now + timedelta(minutes=REALTIME_CACHE_EXPIRY_MINUTES)
            logger.debug(f"🔄 Cache de configs activas renovado: {len(self._active_configs_cache)} bots")
        
        return self._active_configs_cache

    def _is_bot_ready_for_realtime(self, config: GridConfig) -> bool:
        """
        Verifica si un bot está listo para monitoreo en tiempo real.
        Un bot está listo cuando:
        1. Ha completado su primera inicialización (100% de órdenes iniciales)
        2. O ya está operando normalmente (primera inicialización completada)
        
        Args:
            config: Configuración del bot
            
        Returns:
            bool: True si el bot está listo para monitoreo en tiempo real
        """
        pair = config.pair
        
        # Verificar cache de estado de inicialización
        now = datetime.now()
        last_check = self._bot_initialization_status.get(pair, {}).get('last_check')
        
        # Solo verificar cada 30 segundos para evitar spam de logs
        if last_check and (now - last_check).total_seconds() < self._initialization_check_interval:
            return self._bot_initialization_status.get(pair, {}).get('initialized', False)
        
        try:
            # Obtener órdenes activas actuales
            current_active_orders = self.exchange_service.get_active_orders_from_exchange(pair)
            total_active_orders = len(current_active_orders)
            
            # Verificar si ya completó la primera inicialización
            first_init_completed = self._bot_initialization_status.get(pair, {}).get('first_initialization_completed', False)
            
            if first_init_completed:
                # Si ya completó la primera inicialización, está listo para operar normalmente
                is_ready = True
                logger.debug(f"✅ Bot {pair} ya completó primera inicialización, operando normalmente")
            else:
                # Verificar si está completando la primera inicialización (100% de órdenes iniciales)
                min_orders_required = config.grid_levels
                is_ready = total_active_orders >= min_orders_required
                
                if is_ready:
                    # Marcar que completó la primera inicialización
                    logger.info(f"🎉 Bot {pair} completó primera inicialización "
                               f"({total_active_orders}/{config.grid_levels} órdenes activas)")
            
            # Actualizar estado de inicialización
            self._bot_initialization_status[pair] = {
                'initialized': is_ready,
                'initial_orders_count': total_active_orders,
                'required_orders': config.grid_levels,
                'first_initialization_completed': first_init_completed or is_ready,
                'last_check': now
            }
            
            if not is_ready and not first_init_completed:
                logger.debug(f"⏳ Bot {pair} aún en primera inicialización: {total_active_orders}/{config.grid_levels} órdenes requeridas")
            
            return is_ready
            
        except Exception as e:
            logger.error(f"❌ Error verificando estado de inicialización para {pair}: {e}")
            return False

    def _monitor_bot_realtime(self, config: GridConfig) -> Dict[str, Any]:
        """
        Monitorea un bot individual en tiempo real usando métodos avanzados de detección de fills.
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con el resultado del monitoreo
        """
        logger.debug(f"⚡ Monitoreando {config.pair} en tiempo real...")
        
        pair = config.pair
        fills_detected = []
        
        # 1. Verificar y limpiar órdenes excedentes antes de continuar
        excess_orders_cancelled = self._cleanup_excess_orders(config)
        if excess_orders_cancelled > 0:
            logger.warning(f"🚦 Bot {pair}: {excess_orders_cancelled} órdenes excedentes canceladas antes del monitoreo")
        
        # 2. Obtener órdenes activas actuales del exchange
        current_active_orders = self.exchange_service.get_active_orders_from_exchange(pair)
        logger.debug(f"[EXCHANGE] {pair}: {len(current_active_orders)} órdenes activas")
        
        # 3. Detectar fills usando múltiples métodos
        fills_detected.extend(self._detect_fills_method_1(pair, current_active_orders))
        fills_detected.extend(self._detect_fills_method_2(pair))
        fills_detected.extend(self._detect_fills_method_3(pair))
        
        # 4. Actualizar tracking de órdenes para el próximo ciclo
        self._previous_active_orders[pair] = current_active_orders
        
        # 5. Procesar fills detectados
        new_orders_created = 0
        trades_completed = 0
        
        if fills_detected:
            logger.info(f"💰 {len(fills_detected)} fills detectados en {pair} usando métodos avanzados")
            
            # Eliminar duplicados basados en exchange_order_id
            unique_fills = {}
            for fill in fills_detected:
                order_id = fill.get('exchange_order_id')
                if order_id and order_id not in unique_fills:
                    unique_fills[order_id] = fill
            
            fills_detected = list(unique_fills.values())
            logger.info(f"🔄 {len(fills_detected)} fills únicos procesados en {pair}")
            
            # 🎯 NUEVO: Detectar trades completos
            completed_trades = self._detect_completed_trades(pair, fills_detected)
            trades_completed = len(completed_trades)
            
            for fill in fills_detected:
                logger.info(f"[FILL] {pair}: Orden {fill['exchange_order_id']} {fill['side']} {fill['filled']} a ${fill['price']} ejecutada")
                
                # Crear orden complementaria
                comp_order = self._create_complementary_order_from_dict(fill, config)
                if comp_order:
                    logger.info(f"[COMPLEMENTARIA] {pair}: Orden complementaria creada correctamente")
                    new_orders_created += 1
                else:
                    logger.warning(f"[COMPLEMENTARIA] {pair}: No se pudo crear la orden complementaria")
        
        return {
            'fills_detected': len(fills_detected),
            'new_orders_created': new_orders_created,
            'trades_completed': trades_completed,
            'excess_orders_cancelled': excess_orders_cancelled
        }

    def _detect_fills_method_1(self, pair: str, current_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Método 1: Detección por comparación de órdenes activas.
        Detecta órdenes que desaparecieron del listado de activas.
        """
        try:
            previous_orders = self._previous_active_orders.get(pair, [])
            if not previous_orders:
                return []
            
            fills = self.exchange_service.detect_fills_by_comparison(pair, previous_orders)
            if fills:
                logger.info(f"🔍 Método 1: {len(fills)} fills detectados por comparación en {pair}")
            
            return fills
            
        except Exception as e:
            logger.error(f"❌ Error en método 1 de detección de fills para {pair}: {e}")
            return []

    def _detect_fills_method_2(self, pair: str) -> List[Dict[str, Any]]:
        """
        Método 2: Detección usando fetch_closed_orders.
        Obtiene órdenes cerradas recientemente del exchange.
        SOLO ÓRDENES ACTIVAS ACTUALES - NO HISTÓRICAS.
        """
        try:
            # 🔒 SOLO DETECTAR FILLS DE ÓRDENES ACTIVAS ACTUALES
            # Obtener órdenes activas actuales
            current_active_orders = self.exchange_service.get_active_orders_from_exchange(pair)
            if not current_active_orders:
                return []
            
            # Crear set de IDs de órdenes activas para verificación rápida
            active_order_ids = {order['exchange_order_id'] for order in current_active_orders}
            
            # Obtener fills desde hace 2 minutos (ventana más corta para evitar históricos)
            since_timestamp = int((datetime.now().timestamp() - 120) * 1000)  # 2 minutos atrás
            
            fills = self.exchange_service.get_filled_orders_from_exchange(pair, since_timestamp)
            
            # 🔒 FILTRAR: Solo fills de órdenes que estaban activas
            valid_fills = []
            for fill in fills:
                order_id = fill.get('exchange_order_id')
                if order_id and order_id in active_order_ids:
                    valid_fills.append(fill)
                else:
                    logger.debug(f"🔍 Fill ignorado (orden no activa): {order_id} en {pair}")
            
            if valid_fills:
                logger.info(f"📋 Método 2: {len(valid_fills)} fills válidos de {len(fills)} total en {pair}")
            
            return valid_fills
            
        except Exception as e:
            logger.error(f"❌ Error en método 2 de detección de fills para {pair}: {e}")
            return []

    def _detect_fills_method_3(self, pair: str) -> List[Dict[str, Any]]:
        """
        Método 3: Detección usando fetch_my_trades.
        Obtiene trades recientes para detectar fills.
        SOLO ÓRDENES ACTIVAS ACTUALES - NO HISTÓRICAS.
        """
        try:
            # 🔒 SOLO DETECTAR FILLS DE ÓRDENES ACTIVAS ACTUALES
            # Obtener órdenes activas actuales
            current_active_orders = self.exchange_service.get_active_orders_from_exchange(pair)
            if not current_active_orders:
                return []
            
            # Crear set de IDs de órdenes activas para verificación rápida
            active_order_ids = {order['exchange_order_id'] for order in current_active_orders}
            
            # Obtener trades desde hace 2 minutos (ventana más corta)
            since_timestamp = int((datetime.now().timestamp() - 120) * 1000)  # 2 minutos atrás
            
            trades = self.exchange_service.get_recent_trades_from_exchange(pair, since_timestamp)
            if not trades:
                return []
            
            # Convertir trades a formato de fills, SOLO DE ÓRDENES ACTIVAS
            fills = []
            for trade in trades:
                order_id = trade.get('order_id')
                if order_id and order_id in active_order_ids:
                    order_status = self.exchange_service.get_order_status_from_exchange(pair, order_id)
                    if order_status and order_status['status'] == 'closed':
                        fills.append(order_status)
                        logger.debug(f"💱 Fill válido detectado: {order_id} en {pair}")
                else:
                    logger.debug(f"💱 Trade ignorado (orden no activa): {order_id} en {pair}")
            
            if fills:
                logger.info(f"💱 Método 3: {len(fills)} fills válidos de trades en {pair}")
            
            return fills
            
        except Exception as e:
            logger.error(f"❌ Error en método 3 de detección de fills para {pair}: {e}")
            return []

    def _detect_completed_trades(self, pair: str, filled_orders: List[Dict[str, Any]]) -> List[GridTrade]:
        """
        Detecta trades completos (compra + venta) y calcula P&L real.
        
        Args:
            pair: Par de trading
            filled_orders: Lista de órdenes completadas
            
        Returns:
            Lista de trades completos detectados
        """
        completed_trades = []
        
        try:
            for filled_order in filled_orders:
                order_id = filled_order.get('exchange_order_id')
                side = filled_order.get('side')
                price = Decimal(str(filled_order.get('price', 0)))
                amount = Decimal(str(filled_order.get('filled', 0)))
                timestamp = datetime.now()
                
                if side == 'buy':
                    # Registrar compra pendiente
                    if pair not in self._pending_buys:
                        self._pending_buys[pair] = {}
                    
                    self._pending_buys[pair][order_id] = {
                        'price': price,
                        'amount': amount,
                        'timestamp': timestamp
                    }
                    logger.debug(f"📈 Compra registrada para {pair}: {amount} a ${price}")
                    
                elif side == 'sell':
                    # Buscar compra correspondiente para completar el trade
                    if pair in self._pending_buys and self._pending_buys[pair]:
                        # Encontrar la compra más antigua (FIFO)
                        oldest_buy_id = min(self._pending_buys[pair].keys(), 
                                          key=lambda k: self._pending_buys[pair][k]['timestamp'])
                        buy_data = self._pending_buys[pair][oldest_buy_id]
                        
                        # Verificar que las cantidades coincidan (aproximadamente)
                        if abs(buy_data['amount'] - amount) < Decimal('0.000001'):
                            # Crear trade completo
                            profit = (price - buy_data['price']) * amount
                            profit_percent = (profit / (buy_data['price'] * amount) * 100) if buy_data['price'] > 0 else Decimal('0')
                            
                            trade = GridTrade(
                                pair=pair,
                                buy_order_id=str(oldest_buy_id),
                                sell_order_id=str(order_id),
                                buy_price=buy_data['price'],
                                sell_price=price,
                                amount=amount,
                                profit=profit,
                                profit_percent=profit_percent,
                                executed_at=timestamp
                            )
                            
                            completed_trades.append(trade)
                            
                            # Guardar trade en el repositorio
                            self.grid_repository.save_trade(trade)
                            
                            # Remover la compra pendiente
                            del self._pending_buys[pair][oldest_buy_id]
                            
                            logger.info(f"🎯 Trade completo detectado en {pair}: Compra ${buy_data['price']:.4f} → Venta ${price:.4f} = Profit ${profit:.4f} ({profit_percent:.2f}%)")
                        else:
                            logger.warning(f"⚠️ Cantidades no coinciden en {pair}: Compra {buy_data['amount']} vs Venta {amount}")
                    else:
                        logger.warning(f"⚠️ Venta sin compra correspondiente en {pair}: {amount} a ${price}")
            
            return completed_trades
            
        except Exception as e:
            logger.error(f"❌ Error detectando trades completos para {pair}: {e}")
            return completed_trades

    def _create_complementary_order_from_dict(self, filled_order: Dict[str, Any], config: GridConfig) -> Optional[GridOrder]:
        """
        Crea una orden complementaria basada en una orden completada (dict).
        
        Args:
            filled_order: Orden completada como dict del exchange
            config: Configuración del bot
            
        Returns:
            GridOrder creada o None si falla
        """
        try:
            # 🔒 VALIDACIÓN: Evitar crear órdenes complementarias durante la inicialización
            # Verificar si el bot tiene órdenes iniciales suficientes
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            total_active_orders = len(active_orders)
            
            # Verificar si el bot ha completado su primera inicialización
            first_init_completed = self._bot_initialization_status.get(config.pair, {}).get('first_initialization_completed', False)
            
            if not first_init_completed:
                # Si no ha completado la primera inicialización, verificar que tenga todas las órdenes iniciales
                if total_active_orders < config.grid_levels:
                    logger.info(f"🚫 Bot {config.pair}: Solo {total_active_orders}/{config.grid_levels} órdenes activas. "
                               f"Esperando a completar primera inicialización antes de crear órdenes complementarias.")
                    return None
                else:
                    # Marcar que completó la primera inicialización
                    self._bot_initialization_status[config.pair] = {
                        **self._bot_initialization_status.get(config.pair, {}),
                        'first_initialization_completed': True
                    }
                    logger.info(f"🎉 Bot {config.pair} completó primera inicialización, ahora puede crear órdenes complementarias")
            
            # Verificar límite de órdenes activas ANTES de crear la orden complementaria
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            total_active_orders = len(active_orders)
            max_allowed_orders = config.grid_levels
            
            if total_active_orders >= max_allowed_orders:
                logger.warning(f"🚦 Bot {config.pair}: Límite de órdenes alcanzado ({total_active_orders}/{max_allowed_orders}). No se crea nueva orden complementaria.")
                return None
            
            # Extraer información de la orden completada
            side = filled_order['side']
            filled_amount = filled_order['filled']
            executed_price = filled_order['price']
            
            # Determinar lado complementario
            complementary_side = 'sell' if side == 'buy' else 'buy'
            
            # Calcular precio complementario
            complementary_price = self._calculate_complementary_price(executed_price, config, complementary_side)
            
            # Validar que el bot puede usar el capital
            capital_check = self.exchange_service.can_bot_use_capital(
                config, filled_amount, complementary_side
            )
            
            if not capital_check['can_use']:
                logger.warning(f"🚫 Bot {config.pair} no puede crear orden complementaria: {capital_check}")
                return None
            
            # Crear orden complementaria
            complementary_order = self.exchange_service.create_order(
                pair=config.pair,
                side=complementary_side,
                amount=filled_amount,
                price=complementary_price,
                order_type='limit'
            )
            
            if complementary_order:
                logger.info(f"✅ Orden complementaria creada: {complementary_side} {filled_amount} a ${complementary_price}")
                
                # 📱 Acumular notificación en lugar de enviar inmediatamente
                notification = {
                    'pair': config.pair,
                    'side': complementary_side.upper(),
                    'amount': filled_amount,
                    'price': complementary_price,
                    'bot_type': config.config_type,
                    'timestamp': datetime.now()
                }
                self._complementary_orders_notifications.append(notification)
                
                return complementary_order
            else:
                logger.error(f"❌ Error creando orden complementaria en {config.pair}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en _create_complementary_order_from_dict para {config.pair}: {e}")
            return None

    def _check_filled_orders_optimized(self, active_orders: List[GridOrder], pair: str) -> List[GridOrder]:
        """
        Verifica fills de manera optimizada para tiempo real.
        Solo revisa órdenes que no hemos verificado recientemente.
        """
        filled_orders = []
        now = datetime.now()
        
        # Filtrar órdenes que necesitan verificación
        orders_to_check = []
        for order in active_orders:
            if order.status != 'open' or not order.exchange_order_id:
                continue
                
            # Verificar si la orden necesita ser revisada
            last_check_key = f"{pair}_{order.exchange_order_id}"
            last_check = self._last_check_time.get(last_check_key)
            
            # Verificar si han pasado al menos 5 segundos desde la última revisión
            if last_check is None or (now - last_check).total_seconds() >= 5:
                orders_to_check.append(order)
                self._last_check_time[last_check_key] = now
        
        # Verificar estado en el exchange
        for order in orders_to_check:
            try:
                order_status = self.exchange_service.get_order_status(pair, order.exchange_order_id)
                
                if order_status.get('status') == 'closed':
                    # Actualizar estado en BD
                    self.grid_repository.update_order_status(
                        order.exchange_order_id,
                        'filled',
                        datetime.now()
                    )
                    
                    # Actualizar orden en memoria
                    order.status = 'filled'
                    order.filled_at = datetime.now()
                    filled_orders.append(order)
                    
                    logger.info(f"⚡ FILL detectado: {order.side} {order.amount} {pair} a ${order.price}")
                    
            except Exception as e:
                logger.error(f"❌ Error verificando orden {order.exchange_order_id}: {e}")
                continue
        
        return filled_orders

    def _create_complementary_order(self, filled_order: GridOrder, config: GridConfig) -> Optional[GridOrder]:
        """
        Crea inmediatamente la orden complementaria para una orden completada.
        RESPETA AISLAMIENTO DE CAPITAL: Cada bot solo usa su capital asignado.
        CONTROL DE LÍMITE: Nunca más órdenes activas que niveles de grid.
        """
        try:
            current_price = self.exchange_service.get_current_price(config.pair)
            
            # 🔒 VALIDACIÓN: Evitar crear órdenes complementarias durante la inicialización
            # Verificar si el bot tiene órdenes iniciales suficientes
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            total_active_orders = len(active_orders)
            
            # Verificar si el bot ha completado su primera inicialización
            first_init_completed = self._bot_initialization_status.get(config.pair, {}).get('first_initialization_completed', False)
            
            if not first_init_completed:
                # Si no ha completado la primera inicialización, verificar que tenga todas las órdenes iniciales
                if total_active_orders < config.grid_levels:
                    logger.info(f"🚫 Bot {config.pair}: Solo {total_active_orders}/{config.grid_levels} órdenes activas. "
                               f"Esperando a completar primera inicialización antes de crear órdenes complementarias.")
                    return None
                else:
                    # Marcar que completó la primera inicialización
                    self._bot_initialization_status[config.pair] = {
                        **self._bot_initialization_status.get(config.pair, {}),
                        'first_initialization_completed': True
                    }
                    logger.info(f"🎉 Bot {config.pair} completó primera inicialización, ahora puede crear órdenes complementarias")
            
            # Verificar límite de órdenes activas
            max_allowed_orders = config.grid_levels
            
            if total_active_orders >= max_allowed_orders:
                logger.warning(f"🚦 Bot {config.pair}: Límite de órdenes alcanzado ({total_active_orders}/{max_allowed_orders}). No se crea nueva orden.")
                return None
            
            if filled_order.side == 'buy':
                # Crear orden de venta - USAR CANTIDAD NETA DESPUÉS DE COMISIONES
                sell_price = self._calculate_complementary_price(filled_order.price, config, 'sell')
                
                # Calcular cantidad neta que realmente recibimos después de comisiones
                net_amount_received = self.exchange_service.calculate_net_amount_after_fees(
                    gross_amount=filled_order.amount,
                    price=filled_order.price,
                    side='buy',
                    pair=config.pair
                )
                
                # Validar que la orden de venta cumple con el mínimo después de comisiones
                sell_validation = self.exchange_service.validate_order_after_fees(
                    pair=config.pair,
                    side='sell',
                    amount=net_amount_received,
                    price=sell_price
                )
                
                if sell_validation['valid']:
                    # Verificar que el bot puede usar esta cantidad para venta
                    sell_check = self.exchange_service.can_bot_use_capital(config, net_amount_received, 'sell')
                    
                    if sell_check['can_use']:
                        order = self.exchange_service.create_order(
                            pair=config.pair,
                            side='sell',
                            amount=net_amount_received,  # Usar cantidad neta
                            price=sell_price,
                            order_type='limit'
                        )
                        
                        saved_order = self.grid_repository.save_order(order)
                        logger.info(f"⚡ Bot {config.pair}: Orden de venta creada {net_amount_received} a ${sell_price} (neto después de comisiones)")
                        return saved_order
                    else:
                        logger.warning(f"⚠️ Bot {config.pair}: No puede vender {net_amount_received}. Disponible: {sell_check['available_balance']}")
                        return None
                else:
                    logger.warning(f"⚠️ Bot {config.pair}: Orden de venta no cumple mínimo después de comisiones: ${sell_validation['net_value']:.2f} < ${sell_validation['min_required']}")
                    return None
                    
            elif filled_order.side == 'sell':
                # Crear orden de compra - USAR CAPITAL ASIGNADO AL BOT
                buy_price = self._calculate_complementary_price(filled_order.price, config, 'buy')
                
                # Calcular cuánto USDT realmente recibimos después de comisiones de la venta
                gross_usdt_received = filled_order.amount * filled_order.price
                net_usdt_received = self.exchange_service.calculate_net_amount_after_fees(
                    gross_amount=filled_order.amount,
                    price=filled_order.price,
                    side='sell',
                    pair=config.pair
                ) * filled_order.price
                
                # Calcular cantidad a comprar con el USDT neto recibido
                amount_to_buy = (net_usdt_received / buy_price).quantize(Decimal('0.000001'))
                order_value = buy_price * amount_to_buy
                
                # Validar que la orden de compra cumple con el mínimo después de comisiones
                buy_validation = self.exchange_service.validate_order_after_fees(
                    pair=config.pair,
                    side='buy',
                    amount=amount_to_buy,
                    price=buy_price
                )
                
                if buy_validation['valid']:
                    # Verificar que el bot puede usar este capital para compra
                    buy_check = self.exchange_service.can_bot_use_capital(config, order_value, 'buy')
                    
                    if buy_check['can_use']:
                        order = self.exchange_service.create_order(
                            pair=config.pair,
                            side='buy',
                            amount=amount_to_buy,
                            price=buy_price,
                            order_type='limit'
                        )
                        
                        saved_order = self.grid_repository.save_order(order)
                        logger.info(f"⚡ Bot {config.pair}: Orden de compra creada {amount_to_buy} a ${buy_price} (con USDT neto: ${net_usdt_received:.2f})")
                        return saved_order
                    else:
                        logger.warning(f"⚠️ Bot {config.pair}: No puede comprar con ${order_value} USDT. Disponible: ${buy_check['available_balance']}")
                        return None
                else:
                    logger.warning(f"⚠️ Bot {config.pair}: Orden de compra no cumple mínimo después de comisiones: ${buy_validation['net_value']:.2f} < ${buy_validation['min_required']}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creando orden complementaria para bot {config.pair}: {e}")
            return None

    def _calculate_complementary_price(self, base_price: Decimal, config: GridConfig, side: str) -> Decimal:
        """Calcula el precio de la orden complementaria."""
        spread_percent = config.price_range_percent / config.grid_levels
        spread_factor = Decimal(spread_percent / 100)
        
        if side == 'sell':
            return base_price * (1 + spread_factor)
        else:  # buy
            return base_price * (1 - spread_factor)

    def _create_trade_record(self, sell_order: GridOrder, config: GridConfig) -> Optional[GridTrade]:
        """Crea un registro de trade completado para notificaciones."""
        try:
            # Buscar la orden de compra correspondiente (simplificado)
            buy_price = self._calculate_complementary_price(sell_order.price, config, 'buy')
            
            profit = (sell_order.price - buy_price) * sell_order.amount
            profit_percent = Decimal((profit / (buy_price * sell_order.amount)) * 100) if buy_price > 0 else Decimal(0)
            
            return GridTrade(
                pair=sell_order.pair,
                buy_order_id='estimated',  # En implementación real, buscar orden relacionada
                sell_order_id=sell_order.exchange_order_id or '',
                buy_price=buy_price,
                sell_price=sell_order.price,
                amount=sell_order.amount,
                profit=profit,
                profit_percent=profit_percent,
                executed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error creando registro de trade: {e}")
            return None

    def clear_cache(self):
        """Limpia el cache de configuraciones activas."""
        self._active_configs_cache = []
        self._cache_expiry = None
        logger.debug("🧹 Cache de configuraciones limpiado")

    def reset_initialization_status(self, pair: Optional[str] = None):
        """
        Resetea el estado de inicialización para un bot específico o todos los bots.
        
        Args:
            pair: Par específico a resetear, o None para resetear todos
        """
        if pair:
            if pair in self._bot_initialization_status:
                del self._bot_initialization_status[pair]
                logger.info(f"🔄 Estado de inicialización reseteado para {pair}")
        else:
            self._bot_initialization_status.clear()
            logger.info("🔄 Estado de inicialización reseteado para todos los bots")

    def reset_initialization_status_for_paused_bot(self, pair: str):
        """
        Resetea el estado de inicialización específicamente para un bot pausado.
        Esto asegura que cuando se reactive, pase por el proceso de inicialización completo.
        
        Args:
            pair: Par del bot pausado
        """
        if pair in self._bot_initialization_status:
            del self._bot_initialization_status[pair]
            logger.info(f"🔄 Estado de inicialización reseteado para bot pausado {pair}")
        else:
            logger.debug(f"ℹ️ No había estado de inicialización para resetear en {pair}")

    def get_initialization_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de inicialización de todos los bots.
        
        Returns:
            Dict con el estado de inicialización de cada bot
        """
        return self._bot_initialization_status.copy()

    def get_accumulated_complementary_notifications(self) -> List[Dict[str, Any]]:
        """
        Obtiene las notificaciones de órdenes complementarias acumuladas.
        
        Returns:
            Lista de notificaciones acumuladas
        """
        return self._complementary_orders_notifications.copy()

    def get_total_trades_count(self) -> int:
        """
        Obtiene el conteo total de trades acumulados.
        
        Returns:
            Número total de trades acumulados
        """
        return len(self._complementary_orders_notifications)

    def get_trades_count_by_pair(self, pair: str) -> int:
        """
        Obtiene el conteo de trades acumulados para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            
        Returns:
            Número de trades acumulados para el par
        """
        return len([n for n in self._complementary_orders_notifications if n.get('pair') == pair])

    def clear_accumulated_notifications(self) -> None:
        """
        Limpia las notificaciones acumuladas después de enviarlas.
        """
        self._complementary_orders_notifications.clear()
        self._last_notification_cleanup = datetime.now()
        logger.debug("🧹 Notificaciones de órdenes complementarias limpiadas")

    def format_complementary_orders_summary(self) -> str:
        """
        Formatea un resumen de las órdenes complementarias acumuladas.
        
        Returns:
            String formateado con el resumen de órdenes complementarias
        """
        if not self._complementary_orders_notifications:
            return ""
        
        # Agrupar por par
        orders_by_pair = {}
        for notification in self._complementary_orders_notifications:
            pair = notification['pair']
            if pair not in orders_by_pair:
                orders_by_pair[pair] = []
            orders_by_pair[pair].append(notification)
        
        # Formatear resumen
        summary = "🔄 <b>ÓRDENES COMPLEMENTARIAS CREADAS</b>\n\n"
        
        total_orders = len(self._complementary_orders_notifications)
        total_buy = sum(1 for order in self._complementary_orders_notifications if order['side'] == 'BUY')
        total_sell = sum(1 for order in self._complementary_orders_notifications if order['side'] == 'SELL')
        
        summary += f"📊 <b>Total general:</b> {total_orders} órdenes ({total_buy} compras, {total_sell} ventas)\n\n"
        
        for pair, orders in orders_by_pair.items():
            summary += f"💱 <b>{pair}</b>\n"
            buy_count = sum(1 for order in orders if order['side'] == 'BUY')
            sell_count = sum(1 for order in orders if order['side'] == 'SELL')
            
            summary += f"   📈 Compras: {buy_count} órdenes\n"
            summary += f"   📉 Ventas: {sell_count} órdenes\n"
            summary += f"   🔄 Total: {len(orders)} órdenes\n\n"
        
        # Mostrar período de tiempo
        if self._complementary_orders_notifications:
            first_time = min(order['timestamp'] for order in self._complementary_orders_notifications)
            last_time = max(order['timestamp'] for order in self._complementary_orders_notifications)
            summary += f"⏰ <b>Período:</b> {first_time.strftime('%H:%M:%S')} - {last_time.strftime('%H:%M:%S')}"
        
        return summary

    # ------------------------------------------------------------------
    # NUEVA LÓGICA BASADA EN GRIDSTEP
    # ------------------------------------------------------------------

    def _process_grid_steps(self, config: GridConfig, filled_orders: List[GridOrder]):
        """Actualiza los GridStep según las órdenes llenadas y crea la orden complementaria
        alternando el side para cada escalón.
        CONTROL DE LÍMITE: Nunca más órdenes activas que niveles de grid.
        """
        steps = self.grid_repository.get_grid_steps(config.pair) or []
        steps_by_level = {s.level_index: s for s in steps}

        new_orders_created = 0
        trades_completed = 0
        
        # Verificar límite de órdenes activas antes de procesar
        active_orders = self.grid_repository.get_active_orders(config.pair)
        total_active_orders = len(active_orders)
        max_allowed_orders = config.grid_levels
        
        if total_active_orders >= max_allowed_orders:
            logger.warning(f"🚦 Bot {config.pair}: Límite de órdenes alcanzado ({total_active_orders}/{max_allowed_orders}). No se procesan nuevas órdenes.")
            return new_orders_created, trades_completed

        for order in filled_orders:
            step = steps_by_level.get(order.grid_level)
            if not step:
                logger.warning(f"⚠️ No se encontró GridStep para nivel {order.grid_level} en {config.pair}")
                continue

            # Registrar último side llenado
            step.last_filled_side = order.side

            # Alternar side
            next_side = 'sell' if order.side == 'buy' else 'buy'

            price = self._calculate_complementary_price(order.price, config, next_side)
            order_value = price * order.amount

            if order_value < Decimal(MIN_ORDER_VALUE_USDT):
                logger.debug(f"🔸 Valor de orden menor al mínimo, se omite crear para nivel {step.level_index}")
                step.active_order_id = None
                step.active_side = None
                continue

            # Crear nueva orden
            try:
                new_order = self.exchange_service.create_order(
                    pair=config.pair,
                    side=next_side,
                    amount=order.amount,
                    price=price,
                    order_type='limit'
                )
                saved_order = self.grid_repository.save_order(new_order)
                new_orders_created += 1

                # Actualizar GridStep
                step.active_order_id = saved_order.exchange_order_id
                step.active_side = next_side

                if next_side == 'sell':
                    # Si creamos venta, registramos trade
                    trade = self._create_trade_record(saved_order, config)
                    if trade:
                        self.notification_service.send_trade_notification(trade)
                        trades_completed += 1

            except Exception as e:
                logger.error(f"❌ Error creando orden para GridStep {step.level_index}: {e}")
                continue

        # Guardar pasos actualizados
        self.grid_repository.save_grid_steps(config.pair, list(steps_by_level.values()))

        return new_orders_created, trades_completed 

    def _cleanup_excess_orders(self, config: GridConfig) -> int:
        """
        Limpia órdenes excedentes cuando se supera el límite de grid_levels.
        
        Args:
            config: Configuración del bot
            
        Returns:
            int: Número de órdenes canceladas
        """
        try:
            active_orders = self.exchange_service.get_active_orders_from_exchange(config.pair)
            total_active_orders = len(active_orders)
            max_allowed_orders = config.grid_levels
            
            if total_active_orders <= max_allowed_orders:
                return 0
            
            excess_orders = total_active_orders - max_allowed_orders
            logger.warning(f"🚦 Bot {config.pair}: Detectadas {excess_orders} órdenes excedentes ({total_active_orders}/{max_allowed_orders})")
            
            # Ordenar órdenes por precio para cancelar las más alejadas del precio actual
            current_price = self.exchange_service.get_current_price(config.pair)
            
            # Separar órdenes de compra y venta
            buy_orders = [o for o in active_orders if o.get('side') == 'buy']
            sell_orders = [o for o in active_orders if o.get('side') == 'sell']
            
            orders_to_cancel = []
            
            # Cancelar órdenes de compra más alejadas del precio actual
            if buy_orders:
                buy_orders.sort(key=lambda x: abs(Decimal(str(x.get('price', 0))) - current_price), reverse=True)
                orders_to_cancel.extend(buy_orders[:excess_orders])
            
            # Si aún hay exceso, cancelar órdenes de venta más alejadas
            if len(orders_to_cancel) < excess_orders and sell_orders:
                remaining_excess = excess_orders - len(orders_to_cancel)
                sell_orders.sort(key=lambda x: abs(Decimal(str(x.get('price', 0))) - current_price), reverse=True)
                orders_to_cancel.extend(sell_orders[:remaining_excess])
            
            # Cancelar las órdenes seleccionadas
            cancelled_count = 0
            for order in orders_to_cancel:
                try:
                    order_id = order.get('exchange_order_id')
                    if order_id:
                        self.exchange_service.cancel_order(config.pair, order_id)
                        cancelled_count += 1
                        logger.info(f"🚫 Orden excedente cancelada: {order.get('side')} {order.get('amount')} a ${order.get('price')}")
                except Exception as e:
                    logger.error(f"❌ Error cancelando orden excedente: {e}")
                    continue
            
            if cancelled_count > 0:
                logger.info(f"✅ Bot {config.pair}: {cancelled_count} órdenes excedentes canceladas")
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"❌ Error limpiando órdenes excedentes para {config.pair}: {e}")
            return 0 