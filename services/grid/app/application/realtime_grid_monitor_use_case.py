"""
Caso de uso para monitoreo en tiempo real de órdenes de Grid Trading.
Optimizado para detectar fills inmediatamente y crear órdenes complementarias.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService, GridCalculator
from app.domain.entities import GridConfig, GridOrder, GridTrade
from app.config import MIN_ORDER_VALUE_USDT, REALTIME_CACHE_EXPIRY_MINUTES
from shared.services.logging_config import get_logger

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
        
        # Cache para optimizar consultas
        self._last_check_time = {}
        self._active_configs_cache = []
        self._cache_expiry = None
        
        logger.info("✅ RealTimeGridMonitorUseCase inicializado.")

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo de monitoreo en tiempo real.
        
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
            
            # 2. Monitorear cada bot activo
            total_fills = 0
            total_new_orders = 0
            total_trades = 0
            
            for config in active_configs:
                try:
                    result = self._monitor_bot_realtime(config)
                    
                    total_fills += result.get('fills_detected', 0)
                    total_new_orders += result.get('new_orders_created', 0)
                    total_trades += result.get('trades_completed', 0)
                    
                except Exception as e:
                    logger.error(f"❌ Error en monitoreo tiempo real para {config.pair}: {e}")
                    continue
            
            # 3. Log resumen solo si hubo actividad
            if total_fills > 0 or total_new_orders > 0:
                logger.info(f"⚡ RT Monitor: {len(active_configs)} bots, {total_fills} fills, {total_new_orders} nuevas órdenes")
            
            return {
                'success': True,
                'monitored_bots': len(active_configs),
                'fills_detected': total_fills,
                'orders_created': total_new_orders,
                'trades_completed': total_trades
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

    def _monitor_bot_realtime(self, config: GridConfig) -> Dict[str, Any]:
        """
        Monitorea un bot individual en tiempo real.
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con el resultado del monitoreo
        """
        logger.debug(f"⚡ Monitoreando {config.pair} en tiempo real...")
        
        # 1. Obtener órdenes activas
        active_orders = self.grid_repository.get_active_orders(config.pair)
        
        if not active_orders:
            logger.debug(f"ℹ️ No hay órdenes activas para {config.pair}")
            return {
                'fills_detected': 0,
                'new_orders_created': 0,
                'trades_completed': 0
            }
        
        # 2. Verificar fills de manera eficiente
        filled_orders = self._check_filled_orders_optimized(active_orders, config.pair)
        
        # 3. Procesar fills inmediatamente
        new_orders_created = 0
        trades_completed = 0
        
        if filled_orders:
            logger.info(f"💰 {len(filled_orders)} órdenes completadas en {config.pair}")
            
            for order in filled_orders:
                try:
                    # Crear orden complementaria inmediatamente
                    complementary_order = self._create_complementary_order(order, config)
                    if complementary_order:
                        new_orders_created += 1
                        
                    # Notificar trade si es de venta (ganancia realizada)
                    if order.side == 'sell':
                        trade = self._create_trade_record(order, config)
                        if trade:
                            self.notification_service.send_trade_notification(trade)
                            trades_completed += 1
                            
                except Exception as e:
                    logger.error(f"❌ Error procesando fill {order.exchange_order_id}: {e}")
                    continue
        
        return {
            'fills_detected': len(filled_orders),
            'new_orders_created': new_orders_created,
            'trades_completed': trades_completed
        }

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
        """
        try:
            current_price = self.exchange_service.get_current_price(config.pair)
            
            if filled_order.side == 'buy':
                # Crear orden de venta
                sell_price = self._calculate_complementary_price(filled_order.price, config, 'sell')
                
                order_value = sell_price * filled_order.amount
                if order_value >= Decimal(MIN_ORDER_VALUE_USDT):
                    order = self.exchange_service.create_order(
                        pair=config.pair,
                        side='sell',
                        amount=filled_order.amount,
                        price=sell_price,
                        order_type='limit'
                    )
                    
                    saved_order = self.grid_repository.save_order(order)
                    logger.info(f"⚡ Orden de venta creada: {order.amount} {config.pair} a ${sell_price}")
                    return saved_order
                    
            elif filled_order.side == 'sell':
                # Crear orden de compra
                buy_price = self._calculate_complementary_price(filled_order.price, config, 'buy')
                
                order_value = buy_price * filled_order.amount
                if order_value >= Decimal(MIN_ORDER_VALUE_USDT):
                    order = self.exchange_service.create_order(
                        pair=config.pair,
                        side='buy',
                        amount=filled_order.amount,
                        price=buy_price,
                        order_type='limit'
                    )
                    
                    saved_order = self.grid_repository.save_order(order)
                    logger.info(f"⚡ Orden de compra creada: {order.amount} {config.pair} a ${buy_price}")
                    return saved_order
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creando orden complementaria: {e}")
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