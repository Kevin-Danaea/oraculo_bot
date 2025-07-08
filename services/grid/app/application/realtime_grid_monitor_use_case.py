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
            risk_events = 0
            
            for config in active_configs:
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
            
            # 3. Log resumen solo si hubo actividad
            if total_fills > 0 or total_new_orders > 0 or risk_events > 0:
                logger.info(f"⚡ RT Monitor: {len(active_configs)} bots, {total_fills} fills, {total_new_orders} nuevas órdenes, {risk_events} eventos de riesgo")
            
            return {
                'success': True,
                'monitored_bots': len(active_configs),
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
            
            new_orders, trades = self._process_grid_steps(config, filled_orders)
            new_orders_created += new_orders
            trades_completed += trades
        
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
        RESPETA AISLAMIENTO DE CAPITAL: Cada bot solo usa su capital asignado.
        CONTROL DE LÍMITE: Nunca más órdenes activas que niveles de grid.
        """
        try:
            current_price = self.exchange_service.get_current_price(config.pair)
            
            # Verificar límite de órdenes activas
            active_orders = self.grid_repository.get_active_orders(config.pair)
            total_active_orders = len(active_orders)
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