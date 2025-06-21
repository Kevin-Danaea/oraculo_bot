import ccxt
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from app.core.logging_config import get_logger
from app.core.config import settings
from app.services.telegram_service import send_telegram_message, send_grid_trade_notification, send_grid_hourly_summary

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

PROFIT_PERCENTAGE = 0.01  # 1% de ganancia por trade
MONITORING_INTERVAL = 30  # segundos entre chequeos
STATUS_REPORT_CYCLES = 120  # enviar resumen cada 120 ciclos (1 hora)
ORDER_RETRY_ATTEMPTS = 3
RECONNECTION_DELAY = 5  # segundos
MAX_RECONNECTION_ATTEMPTS = 5

# Archivo para persistir estado del bot
STATE_FILE = "logs/grid_bot_state.json"

# ============================================================================
# UTILIDADES DE VALIDACIÓN Y CONFIGURACIÓN
# ============================================================================

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y normaliza la configuración del grid bot
    
    Args:
        config: Configuración cruda del bot
        
    Returns:
        Configuración validada y normalizada
        
    Raises:
        ValueError: Si la configuración es inválida
    """
    try:
        # Validar campos requeridos
        required_fields = ['pair', 'total_capital', 'grid_levels', 'price_range_percent']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Campo requerido faltante: {field}")
        
        # Validar tipos y rangos
        pair = str(config['pair']).upper()
        total_capital = float(config['total_capital'])
        grid_levels = int(config['grid_levels'])
        price_range_percent = float(config['price_range_percent'])
        
        if total_capital <= 0:
            raise ValueError("El capital total debe ser mayor a 0")
        if grid_levels < 2:
            raise ValueError("Debe haber al menos 2 niveles de grilla")
        if grid_levels > 20:
            raise ValueError("Máximo 20 niveles de grilla permitidos")
        if price_range_percent <= 0 or price_range_percent > 50:
            raise ValueError("El rango de precio debe estar entre 0.1% y 50%")
        
        validated_config = {
            'pair': pair,
            'total_capital': total_capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range_percent,
            'profit_percentage': PROFIT_PERCENTAGE * 100,  # Para logging
            'max_orders_per_side': grid_levels // 2 + 1,
            'min_order_size': total_capital * 0.001  # 0.1% del capital mínimo por orden
        }
        
        logger.info(f"✅ Configuración validada: {validated_config}")
        return validated_config
        
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        raise ValueError(f"Configuración inválida: {e}")


def get_exchange_connection() -> ccxt.Exchange:
    """
    Crea y valida conexión con Binance
    
    Returns:
        Instancia configurada del exchange
        
    Raises:
        ConnectionError: Si no se puede conectar
    """
    try:
        # Validar credenciales
        api_key = settings.BINANCE_API_KEY
        api_secret = settings.BINANCE_API_SECRET
        
        if not api_key or not api_secret:
            raise ConnectionError("Las claves API de Binance no están configuradas")
        
        # Configurar exchange
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 30000,  # 30 segundos timeout
            'rateLimit': 1200,  # ms entre requests
        })
        
        # Verificar conexión y permisos
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        
        logger.info(f"✅ Conexión con Binance establecida")
        logger.info(f"💵 Balance USDT disponible: ${usdt_balance:.2f}")
        
        return exchange
        
    except Exception as e:
        logger.error(f"❌ Error conectando con Binance: {e}")
        raise ConnectionError(f"No se pudo conectar con Binance: {e}")


def reconnect_exchange(max_attempts: int = MAX_RECONNECTION_ATTEMPTS) -> Optional[ccxt.Exchange]:
    """
    Intenta reconectar con el exchange con reintentos
    
    Args:
        max_attempts: Número máximo de intentos
        
    Returns:
        Exchange reconectado o None si falla
    """
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 Intento de reconexión {attempt + 1}/{max_attempts}")
            exchange = get_exchange_connection()
            logger.info("✅ Reconexión exitosa")
            return exchange
        except Exception as e:
            logger.error(f"❌ Intento {attempt + 1} falló: {e}")
            if attempt < max_attempts - 1:
                time.sleep(RECONNECTION_DELAY * (attempt + 1))  # Backoff exponencial
    
    logger.error("❌ No se pudo reconectar después de múltiples intentos")
    return None


# ============================================================================
# GESTIÓN DE ESTADO Y PERSISTENCIA
# ============================================================================

def save_bot_state(active_orders: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    """
    Guarda el estado actual del bot en archivo
    
    Args:
        active_orders: Lista de órdenes activas
        config: Configuración del bot
    """
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        
        state = {
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'active_orders': active_orders,
            'total_orders': len(active_orders)
        }
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
            
        logger.debug(f"💾 Estado guardado: {len(active_orders)} órdenes activas")
        
    except Exception as e:
        logger.error(f"❌ Error guardando estado: {e}")


def load_bot_state() -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Carga el estado previo del bot si existe
    
    Returns:
        Tuple de (órdenes_activas, configuración) o ([], None) si no existe
    """
    try:
        if not os.path.exists(STATE_FILE):
            return [], None
            
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            
        # Verificar que no sea muy antiguo (más de 2 días)
        timestamp = datetime.fromisoformat(state['timestamp'])
        if datetime.now() - timestamp > timedelta(days=2):
            logger.warning("⚠️ Estado guardado muy antiguo, iniciando desde cero")
            return [], None
            
        orders = state.get('active_orders', [])
        config = state.get('config')
        
        logger.info(f"📂 Estado cargado: {len(orders)} órdenes activas")
        return orders, config
        
    except Exception as e:
        logger.error(f"❌ Error cargando estado: {e}")
        return [], None


def clear_bot_state() -> None:
    """
    Elimina el archivo de estado del bot
    """
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            logger.info("🗑️ Archivo de estado eliminado")
        else:
            logger.debug("📁 No hay archivo de estado que eliminar")
    except Exception as e:
        logger.error(f"❌ Error eliminando estado: {e}")


def config_has_significant_changes(saved_config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
    """
    Detecta si hay cambios significativos en la configuración que requieren reiniciar
    
    Args:
        saved_config: Configuración guardada previamente
        new_config: Nueva configuración
        
    Returns:
        True si hay cambios significativos, False si no
    """
    if not saved_config:
        return False
        
    # Campos críticos que requieren reinicio completo
    critical_fields = [
        'pair',
        'total_capital', 
        'grid_levels',
        'price_range_percent'
    ]
    
    changes_detected = []
    
    for field in critical_fields:
        old_value = saved_config.get(field)
        new_value = new_config.get(field)
        
        if old_value != new_value:
            changes_detected.append(f"{field}: {old_value} → {new_value}")
    
    if changes_detected:
        logger.info(f"🔄 Cambios detectados en configuración:")
        for change in changes_detected:
            logger.info(f"   • {change}")
        return True
    
    return False


def cancel_all_active_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]]) -> int:
    """
    Cancela todas las órdenes activas en el exchange
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        
    Returns:
        Número de órdenes canceladas exitosamente
    """
    if not active_orders:
        logger.info("📭 No hay órdenes activas que cancelar")
        return 0
    
    cancelled_count = 0
    logger.info(f"🚫 Iniciando cancelación de {len(active_orders)} órdenes activas...")
    
    for order_info in active_orders:
        try:
            # Verificar si la orden sigue activa antes de cancelar
            order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
            
            if order_status['status'] in ['open', 'partial']:
                # Cancelar la orden
                exchange.cancel_order(order_info['id'], order_info['pair'])
                cancelled_count += 1
                logger.info(f"✅ Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
            else:
                logger.info(f"ℹ️ Orden ya ejecutada/cancelada: {order_info['id']}")
                
        except Exception as e:
            logger.error(f"❌ Error cancelando orden {order_info['id']}: {e}")
            # Continuar con las demás órdenes aunque una falle
    
    logger.info(f"🎯 Cancelación completada: {cancelled_count}/{len(active_orders)} órdenes canceladas")
    return cancelled_count


def reset_bot_for_new_config(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]]) -> None:
    """
    Resetea completamente el bot para nueva configuración
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas a cancelar
    """
    try:
        logger.info("🔄 ========== REINICIANDO BOT CON NUEVA CONFIGURACIÓN ==========")
        
        # 1. Cancelar todas las órdenes activas
        cancelled_orders = cancel_all_active_orders(exchange, active_orders)
        
        # 2. Limpiar estado guardado
        clear_bot_state()
        
        # 3. Enviar notificación
        message = f"🔄 <b>GRID BOT REINICIADO</b>\n\n"
        message += f"🚫 <b>Órdenes canceladas:</b> {cancelled_orders}\n"
        message += f"🗑️ <b>Estado limpiado:</b> ✅\n"
        message += f"🆕 <b>Iniciando con nueva configuración...</b>"
        
        send_telegram_message(message)
        
        logger.info("✅ Reset completado - Bot listo para nueva configuración")
        
    except Exception as e:
        logger.error(f"❌ Error durante el reset del bot: {e}")
        raise


# ============================================================================
# CÁLCULOS DE GRILLA Y PRECIOS
# ============================================================================

def calculate_grid_prices(current_price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula los precios de compra y venta para la grilla
    
    Args:
        current_price: Precio actual del activo
        config: Configuración validada del bot
        
    Returns:
        Dict con listas de precios de compra y venta
    """
    try:
        grid_levels = config['grid_levels']
        price_range_percent = config['price_range_percent']
        
        # Calcular rango de precios
        price_range = current_price * (price_range_percent / 100)
        min_price = current_price - (price_range / 2)
        max_price = current_price + (price_range / 2)
        
        # Dividir niveles entre compras y ventas
        buy_levels = grid_levels // 2
        sell_levels = grid_levels - buy_levels
        
        # Calcular precios de compra (por debajo del precio actual)
        buy_prices = []
        if buy_levels > 0:
            price_step = (current_price - min_price) / buy_levels
            for i in range(buy_levels):
                buy_price = current_price - price_step * (i + 1)
                buy_prices.append(round(buy_price, 2))
        
        # Calcular precios de venta iniciales (solo si tenemos balance del activo)
        sell_prices = []
        if sell_levels > 0:
            price_step = (max_price - current_price) / sell_levels
            for i in range(sell_levels):
                sell_price = current_price + price_step * (i + 1)
                sell_prices.append(round(sell_price, 2))
        
        logger.info(f"📊 Rango: ${min_price:.2f} - ${max_price:.2f}")
        logger.info(f"🟢 Precios compra: {buy_prices}")
        logger.info(f"🔴 Precios venta iniciales: {sell_prices}")
        
        return {
            'buy_prices': buy_prices,
            'sell_prices': sell_prices,
            'price_range': {'min': min_price, 'max': max_price, 'current': current_price}
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculando precios de grilla: {e}")
        raise


def calculate_order_quantity(capital_per_order: float, price: float, min_qty: float = 0.001) -> float:
    """
    Calcula la cantidad para una orden considerando restricciones del exchange
    
    Args:
        capital_per_order: Capital asignado a esta orden
        price: Precio de la orden
        min_qty: Cantidad mínima permitida
        
    Returns:
        Cantidad calculada y redondeada
    """
    try:
        quantity = capital_per_order / price
        
        # Redondear hacia abajo a 6 decimales para evitar errores de precisión
        quantity = float(Decimal(str(quantity)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        
        # Verificar cantidad mínima
        if quantity < min_qty:
            logger.warning(f"⚠️ Cantidad {quantity} menor que mínimo {min_qty}")
            return min_qty
            
        return quantity
        
    except Exception as e:
        logger.error(f"❌ Error calculando cantidad: {e}")
        raise


# ============================================================================
# GESTIÓN DE ÓRDENES
# ============================================================================

def create_order_with_retry(exchange: ccxt.Exchange, order_type: str, pair: str, 
                          quantity: float, price: float, retries: int = ORDER_RETRY_ATTEMPTS) -> Optional[Dict]:
    """
    Crea una orden con reintentos en caso de fallo
    
    Args:
        exchange: Instancia del exchange
        order_type: 'buy' o 'sell'
        pair: Par de trading
        quantity: Cantidad
        price: Precio
        retries: Número de reintentos
        
    Returns:
        Información de la orden creada o None si falla
    """
    for attempt in range(retries):
        try:
            if order_type == 'buy':
                order = exchange.create_limit_buy_order(pair, quantity, price)
            else:
                order = exchange.create_limit_sell_order(pair, quantity, price)
                
            logger.info(f"✅ Orden {order_type} creada: {quantity:.6f} a ${price}")
            return order
            
        except Exception as e:
            logger.error(f"❌ Intento {attempt + 1} falló para orden {order_type}: {e}")
            if attempt < retries - 1:
                time.sleep(1)  # Esperar antes del siguiente intento
    
    logger.error(f"❌ No se pudo crear orden {order_type} después de {retries} intentos")
    return None


def create_initial_buy_orders(exchange: ccxt.Exchange, config: Dict[str, Any], 
                            grid_prices: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Crea las órdenes de compra iniciales
    
    Args:
        exchange: Instancia del exchange
        config: Configuración del bot
        grid_prices: Precios calculados de la grilla
        
    Returns:
        Lista de órdenes creadas exitosamente
    """
    active_orders = []
    buy_prices = grid_prices['buy_prices']
    
    if not buy_prices:
        logger.warning("⚠️ No hay precios de compra para crear órdenes")
        return active_orders
    
    try:
        pair = config['pair']
        total_capital = config['total_capital']
        capital_per_order = total_capital / len(buy_prices)
        
        logger.info(f"💰 Capital por orden: ${capital_per_order:.2f}")
        
        successful_orders = 0
        for price in buy_prices:
            quantity = calculate_order_quantity(capital_per_order, price)
            
            order = create_order_with_retry(exchange, 'buy', pair, quantity, price)
            if order:
                order_info = {
                    'id': order['id'],
                    'type': 'buy',
                    'quantity': quantity,
                    'price': price,
                    'pair': pair,
                    'status': 'open',
                    'timestamp': order['timestamp'],
                    'created_at': datetime.now().isoformat()
                }
                active_orders.append(order_info)
                successful_orders += 1
            
        logger.info(f"✅ Órdenes de compra creadas: {successful_orders}/{len(buy_prices)}")
        
        return active_orders
        
    except Exception as e:
        logger.error(f"❌ Error creando órdenes iniciales: {e}")
        return active_orders


def create_sell_order_after_buy(exchange: ccxt.Exchange, buy_order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Crea orden de venta después de ejecutarse una compra
    
    Args:
        exchange: Instancia del exchange
        buy_order: Información de la orden de compra ejecutada
        
    Returns:
        Información de la orden de venta creada o None
    """
    try:
        pair = buy_order['pair']
        quantity = buy_order['quantity']
        buy_price = buy_order['price']
        
        # Calcular precio de venta con ganancia
        sell_price = buy_price * (1 + PROFIT_PERCENTAGE)
        sell_price = round(sell_price, 2)
        
        order = create_order_with_retry(exchange, 'sell', pair, quantity, sell_price)
        if not order:
            return None
            
        sell_order_info = {
            'id': order['id'],
            'type': 'sell',
            'quantity': quantity,
            'price': sell_price,
            'pair': pair,
            'status': 'open',
            'timestamp': order['timestamp'],
            'buy_price': buy_price,
            'buy_order_id': buy_order['id'],
            'created_at': datetime.now().isoformat()
        }
        
        # Calcular ganancia esperada
        profit = (sell_price - buy_price) * quantity
        logger.info(f"💰 Orden venta creada: {quantity:.6f} a ${sell_price} (ganancia esperada: ${profit:.2f})")
        
        return sell_order_info
        
    except Exception as e:
        logger.error(f"❌ Error creando orden de venta: {e}")
        return None


def create_replacement_buy_order(exchange: ccxt.Exchange, sell_order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Crea nueva orden de compra después de ejecutarse una venta
    
    Args:
        exchange: Instancia del exchange
        sell_order: Información de la orden de venta ejecutada
        
    Returns:
        Información de la nueva orden de compra o None
    """
    try:
        pair = sell_order['pair']
        quantity = sell_order['quantity']
        original_buy_price = sell_order.get('buy_price', sell_order['price'] / (1 + PROFIT_PERCENTAGE))
        
        order = create_order_with_retry(exchange, 'buy', pair, quantity, original_buy_price)
        if not order:
            return None
            
        new_buy_order = {
            'id': order['id'],
            'type': 'buy',
            'quantity': quantity,
            'price': original_buy_price,
            'pair': pair,
            'status': 'open',
            'timestamp': order['timestamp'],
            'created_at': datetime.now().isoformat(),
            'replacement_for': sell_order['buy_order_id']
        }
        
        logger.info(f"🔄 Orden de compra reemplazada: {quantity:.6f} a ${original_buy_price}")
        return new_buy_order
        
    except Exception as e:
        logger.error(f"❌ Error creando orden de compra de reemplazo: {e}")
        return None


# ============================================================================
# MONITOREO Y LÓGICA PRINCIPAL
# ============================================================================

def check_and_process_filled_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                                   config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Verifica órdenes ejecutadas y procesa las acciones correspondientes
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        
    Returns:
        Tuple de (órdenes_activas_actualizadas, trades_ejecutados)
    """
    updated_orders = []
    trades_executed = 0
    
    for order_info in active_orders:
        try:
            # Verificar estado de la orden
            order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
            
            if order_status['status'] == 'closed':
                trades_executed += 1
                logger.info(f"✅ Trade ejecutado: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
                
                # Enviar notificación
                send_grid_trade_notification(order_info, config)
                
                if order_info['type'] == 'buy':
                    # Crear orden de venta correspondiente
                    sell_order = create_sell_order_after_buy(exchange, order_info)
                    if sell_order:
                        updated_orders.append(sell_order)
                        
                elif order_info['type'] == 'sell':
                    # Crear nueva orden de compra
                    new_buy_order = create_replacement_buy_order(exchange, order_info)
                    if new_buy_order:
                        updated_orders.append(new_buy_order)
            else:
                # Orden sigue activa
                updated_orders.append(order_info)
                
        except Exception as e:
            logger.error(f"❌ Error verificando orden {order_info['id']}: {e}")
            # Mantener la orden en la lista para reintentarlo después
            updated_orders.append(order_info)
    
    return updated_orders, trades_executed


def monitor_grid_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                      config: Dict[str, Any]) -> None:
    """
    Bucle principal de monitoreo de órdenes
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista inicial de órdenes activas
        config: Configuración del bot
    """
    logger.info("🔄 Iniciando monitoreo continuo de órdenes...")
    
    cycle_count = 0
    trades_in_period = 0
    last_state_save = time.time()
    
    try:
        while True:
            cycle_count += 1
            
            try:
                # Verificar y procesar órdenes
                active_orders, new_trades = check_and_process_filled_orders(
                    exchange, active_orders, config
                )
                trades_in_period += new_trades
                
                # Guardar estado cada 10 minutos
                if time.time() - last_state_save > 600:  # 10 minutos
                    save_bot_state(active_orders, config)
                    last_state_save = time.time()
                
                # Enviar resumen periódico
                if cycle_count >= STATUS_REPORT_CYCLES:
                    if trades_in_period > 0:
                        send_grid_hourly_summary(active_orders, config, trades_in_period)
                        logger.info(f"📊 Resumen enviado - Trades: {trades_in_period}, Órdenes activas: {len(active_orders)}")
                    
                    cycle_count = 0
                    trades_in_period = 0
                
                logger.debug(f"👀 Monitoreo ciclo {cycle_count} - Órdenes activas: {len(active_orders)}")
                
            except ccxt.NetworkError as e:
                logger.error(f"🌐 Error de red: {e}")
                reconnected_exchange = reconnect_exchange()
                if not reconnected_exchange:
                    logger.error("❌ No se pudo reconectar, deteniendo bot")
                    break
                exchange = reconnected_exchange
                    
            except Exception as e:
                logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                time.sleep(MONITORING_INTERVAL * 2)  # Esperar más tiempo en caso de error
                continue
            
            # Esperar antes del siguiente ciclo
            time.sleep(MONITORING_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Monitoreo detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico en monitoreo: {e}")
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT</b>\n\n{str(e)}")
    finally:
        # Guardar estado final
        save_bot_state(active_orders, config)
        logger.info("💾 Estado final guardado")


def force_reset_bot(config: Dict[str, Any]) -> None:
    """
    Función para forzar un reset completo del bot manualmente
    
    Args:
        config: Nueva configuración a usar
    """
    try:
        logger.info("🔧 ========== RESET MANUAL DEL BOT ==========")
        
        # Validar nueva configuración (para asegurar que es válida)
        validate_config(config)
        
        # Cargar estado actual
        saved_orders, _ = load_bot_state()
        
        if saved_orders:
            # Conectar y cancelar órdenes
            exchange = get_exchange_connection()
            reset_bot_for_new_config(exchange, saved_orders)
        else:
            # Solo limpiar estado
            clear_bot_state()
            logger.info("🗑️ Estado limpiado (no había órdenes activas)")
        
        logger.info("✅ Reset manual completado")
        
    except Exception as e:
        logger.error(f"❌ Error en reset manual: {e}")
        raise


# ============================================================================
# FUNCIÓN PRINCIPAL (PUNTO DE ENTRADA)
# ============================================================================

def run_grid_trading_bot(config: Dict[str, Any]) -> None:
    """
    Función principal que orquesta todo el proceso del Grid Trading Bot
    
    Args:
        config: Configuración del bot desde el scheduler
    """
    try:
        logger.info("🤖 ========== INICIANDO GRID TRADING BOT ==========")
        
        # Validar configuración
        validated_config = validate_config(config)
        
        # Intentar cargar estado previo
        saved_orders, saved_config = load_bot_state()
        
        # Conectar con exchange (necesario para cancelar órdenes si es requerido)
        exchange = get_exchange_connection()
        
        # Verificar si hay cambios significativos en la configuración
        if saved_orders and saved_config:
            if config_has_significant_changes(saved_config, validated_config):
                logger.info("🔄 Detectados cambios significativos - Reiniciando bot...")
                reset_bot_for_new_config(exchange, saved_orders)
                # Después del reset, inicializar desde cero
                saved_orders, saved_config = [], None
        
        # Si hay estado previo válido y sin cambios significativos, continuar
        if saved_orders and saved_config:
            logger.info(f"📂 Continuando con {len(saved_orders)} órdenes previas")
            active_orders = saved_orders
        else:
            # Inicializar desde cero
            logger.info("🆕 Iniciando configuración nueva")
            
            # Obtener precio actual
            current_price = exchange.fetch_ticker(validated_config['pair'])['last']
            logger.info(f"💹 Precio actual de {validated_config['pair']}: ${current_price}")
            
            # Calcular precios de grilla
            grid_prices = calculate_grid_prices(current_price, validated_config)
            
            # Crear órdenes iniciales
            active_orders = create_initial_buy_orders(exchange, validated_config, grid_prices)
            
            if not active_orders:
                raise Exception("No se pudieron crear órdenes iniciales")
            
            # Enviar notificación de inicio
            startup_message = f"🚀 <b>GRID BOT INICIADO</b>\n\n"
            startup_message += f"📊 <b>Par:</b> {validated_config['pair']}\n"
            startup_message += f"💰 <b>Capital:</b> ${validated_config['total_capital']}\n"
            startup_message += f"🎯 <b>Niveles:</b> {validated_config['grid_levels']}\n"
            startup_message += f"📈 <b>Rango:</b> {validated_config['price_range_percent']}%\n"
            startup_message += f"💹 <b>Precio actual:</b> ${current_price:.2f}\n"
            startup_message += f"🟢 <b>Órdenes creadas:</b> {len(active_orders)}\n"
            startup_message += f"💵 <b>Ganancia objetivo:</b> {validated_config['profit_percentage']}%"
            
            send_telegram_message(startup_message)
        
        # Iniciar monitoreo continuo
        monitor_grid_orders(exchange, active_orders, validated_config)
        
    except Exception as e:
        error_msg = f"❌ Error fatal en Grid Trading Bot: {e}"
        logger.error(error_msg)
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT</b>\n\n{str(e)}")
        raise
    finally:
        logger.info("🛑 ========== GRID TRADING BOT DETENIDO ==========") 