"""
Startup Manager - Gestión de Arranque del Grid Bot V2
Maneja la limpieza de órdenes huérfanas y el modo standby al reiniciar el servidor.
"""

import ccxt
from typing import List, Dict, Any, Optional
from datetime import datetime
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message
from .config_manager import get_exchange_connection, reconnect_exchange
from .state_manager import load_bot_state, clear_bot_state

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES DE STARTUP
# ============================================================================

CLEANUP_RETRY_ATTEMPTS = 3
CLEANUP_DELAY_SECONDS = 2

# Identificadores del bot para detectar órdenes propias
BOT_ORDER_IDENTIFIERS = [
    'GRID_BUY_',
    'GRID_SELL_',
    'Grid_Buy_',
    'Grid_Sell_',
    'GridBot'
]


def cleanup_orphaned_orders() -> Dict[str, Any]:
    """
    Limpia todas las órdenes huérfanas que puedan haber quedado de sesiones anteriores.
    Se ejecuta automáticamente al reiniciar el servicio.
    
    Nuevo comportamiento mejorado:
    1. Primero intenta cancelar órdenes guardadas localmente
    2. Luego consulta TODAS las órdenes abiertas en Binance 
    3. Identifica y cancela órdenes que pertenezcan al bot
    
    Returns:
        Diccionario con el resultado de la limpieza
    """
    cleanup_result = {
        'success': False,
        'orders_cancelled': 0,
        'orders_found': 0,
        'binance_orders_found': 0,
        'binance_orders_cancelled': 0,
        'local_orders_found': 0,
        'local_orders_cancelled': 0,
        'errors': [],
        'timestamp': datetime.now().isoformat(),
        'exchange_connected': False
    }
    
    try:
        logger.info("🧹 ========== INICIANDO LIMPIEZA COMPLETA DE ÓRDENES HUÉRFANAS ==========")
        
        # 1. Intentar conectar con el exchange
        try:
            exchange = get_exchange_connection()
            cleanup_result['exchange_connected'] = True
            logger.info("✅ Conexión con exchange establecida")
        except Exception as e:
            logger.error(f"❌ No se pudo conectar al exchange: {e}")
            cleanup_result['errors'].append(f"Exchange connection: {str(e)}")
            return cleanup_result
        
        # 2. FASE 1: Limpiar órdenes guardadas localmente
        logger.info("📁 === FASE 1: Limpiando órdenes guardadas localmente ===")
        local_result = cleanup_local_saved_orders(exchange)
        cleanup_result['local_orders_found'] = local_result['orders_found']
        cleanup_result['local_orders_cancelled'] = local_result['orders_cancelled']
        cleanup_result['errors'].extend(local_result['errors'])
        
        # 3. FASE 2: Detectar y cancelar órdenes huérfanas en Binance
        logger.info("🌐 === FASE 2: Detectando órdenes huérfanas en Binance ===")
        binance_result = cleanup_binance_orphaned_orders(exchange)
        cleanup_result['binance_orders_found'] = binance_result['orders_found']
        cleanup_result['binance_orders_cancelled'] = binance_result['orders_cancelled']
        cleanup_result['errors'].extend(binance_result['errors'])
        
        # 4. Consolidar resultados
        cleanup_result['orders_found'] = cleanup_result['local_orders_found'] + cleanup_result['binance_orders_found']
        cleanup_result['orders_cancelled'] = cleanup_result['local_orders_cancelled'] + cleanup_result['binance_orders_cancelled']
        cleanup_result['success'] = True
        
        # 5. Limpiar estado guardado
        clear_bot_state()
        
        logger.info(f"✅ ========== LIMPIEZA COMPLETA FINALIZADA ==========")
        logger.info(f"📊 Total órdenes encontradas: {cleanup_result['orders_found']}")
        logger.info(f"🚫 Total órdenes canceladas: {cleanup_result['orders_cancelled']}")
        logger.info(f"   - Locales: {cleanup_result['local_orders_cancelled']}")
        logger.info(f"   - Binance: {cleanup_result['binance_orders_cancelled']}")
        
        # 6. Enviar notificación de limpieza
        saved_orders, saved_config = load_bot_state()
        send_cleanup_notification(cleanup_result, saved_config)
        
        return cleanup_result
        
    except Exception as e:
        error_msg = f"Error crítico en limpieza: {str(e)}"
        logger.error(f"❌ {error_msg}")
        cleanup_result['errors'].append(error_msg)
        return cleanup_result


def cleanup_local_saved_orders(exchange) -> Dict[str, Any]:
    """
    Limpia órdenes que están guardadas en el estado local del bot.
    
    Args:
        exchange: Conexión al exchange
        
    Returns:
        Resultado de la limpieza local
    """
    local_result = {
        'orders_found': 0,
        'orders_cancelled': 0,
        'errors': []
    }
    
    try:
        # Cargar estado previo para obtener órdenes activas
        saved_orders, saved_config = load_bot_state()
        
        if not saved_orders:
            logger.info("ℹ️ No hay órdenes guardadas localmente para limpiar")
            return local_result
        
        local_result['orders_found'] = len(saved_orders)
        logger.info(f"🔍 Encontradas {len(saved_orders)} órdenes guardadas localmente")
        
        # Verificar y cancelar órdenes una por una
        cancelled_count = 0
        for order_info in saved_orders:
            try:
                # Verificar si la orden aún está activa
                order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
                
                if order_status['status'] in ['open', 'pending']:
                    # Cancelar orden activa
                    exchange.cancel_order(order_info['id'], order_info['pair'])
                    cancelled_count += 1
                    logger.info(f"🚫 [LOCAL] Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
                else:
                    logger.info(f"ℹ️ [LOCAL] Orden ya completada: {order_info['id']}")
                    
            except ccxt.OrderNotFound:
                logger.info(f"ℹ️ [LOCAL] Orden no encontrada (posiblemente ya ejecutada): {order_info['id']}")
            except Exception as e:
                error_msg = f"Error procesando orden local {order_info['id']}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                local_result['errors'].append(error_msg)
        
        local_result['orders_cancelled'] = cancelled_count
        return local_result
        
    except Exception as e:
        error_msg = f"Error en limpieza local: {str(e)}"
        logger.error(f"❌ {error_msg}")
        local_result['errors'].append(error_msg)
        return local_result


def cleanup_binance_orphaned_orders(exchange) -> Dict[str, Any]:
    """
    Detecta y cancela órdenes huérfanas directamente desde Binance.
    Esto es crucial cuando el proceso se mata hard y perdemos el estado local.
    
    Args:
        exchange: Conexión al exchange
        
    Returns:
        Resultado de la limpieza en Binance
    """
    binance_result = {
        'orders_found': 0,
        'orders_cancelled': 0,
        'errors': []
    }
    
    try:
        # Obtener configuración actual para saber qué par consultar
        try:
            from ..interfaces.telegram_interface import get_dynamic_grid_config
            config = get_dynamic_grid_config()
            symbol = config.get('pair', '').replace('/', '')  # ETH/USDT -> ETHUSDT
            
            if not symbol:
                logger.warning("⚠️ No hay configuración de par activa, saltando limpieza de Binance")
                return binance_result
                
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener configuración del par: {e}")
            logger.info("⏭️ Saltando limpieza de órdenes específicas en Binance")
            return binance_result
        
        logger.info(f"🌐 Consultando órdenes abiertas para {symbol} en Binance...")
        
        # Obtener SOLO las órdenes del par específico (evita rate limits)
        open_orders = exchange.fetch_open_orders(symbol)
        
        if not open_orders:
            logger.info(f"✅ No hay órdenes abiertas para {symbol} en Binance")
            return binance_result
            
        logger.info(f"🔍 Encontradas {len(open_orders)} órdenes abiertas para {symbol} en Binance")
        
        # Filtrar órdenes que pertenezcan a nuestro bot
        bot_orders = []
        for order in open_orders:
            if is_bot_order(order):
                bot_orders.append(order)
                logger.info(f"🤖 Órden del bot detectada: {order['symbol']} - {order['side']} - ${order['price']} - ID: {order['id']}")
        
        binance_result['orders_found'] = len(bot_orders)
        
        if not bot_orders:
            logger.info("✅ No se detectaron órdenes huérfanas del bot en Binance")
            return binance_result
        
        logger.warning(f"⚠️ DETECTADAS {len(bot_orders)} ÓRDENES HUÉRFANAS DEL BOT EN BINANCE")
        
        # Cancelar cada orden del bot
        cancelled_count = 0
        for order in bot_orders:
            try:
                exchange.cancel_order(order['id'], order['symbol'])
                cancelled_count += 1
                logger.info(f"🚫 [BINANCE] Órden huérfana cancelada: {order['side']} {order['amount']:.6f} {order['symbol']} a ${order['price']}")
                
            except Exception as e:
                error_msg = f"Error cancelando orden de Binance {order['id']}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                binance_result['errors'].append(error_msg)
        
        binance_result['orders_cancelled'] = cancelled_count
        
        if cancelled_count > 0:
            logger.warning(f"🧹 Se cancelaron {cancelled_count} órdenes huérfanas detectadas en Binance")
        
        return binance_result
        
    except Exception as e:
        error_msg = f"Error consultando Binance: {str(e)}"
        logger.error(f"❌ {error_msg}")
        binance_result['errors'].append(error_msg)
        return binance_result


def is_bot_order(order: Dict[str, Any]) -> bool:
    """
    Determina si una orden pertenece a nuestro bot.
    
    Criterios de identificación:
    1. Client Order ID contiene identificadores del bot
    2. Símbolo coincide con pares que usa el bot
    3. Precio y cantidad típicos del grid bot
    
    Args:
        order: Información de la orden
        
    Returns:
        True si la orden pertenece al bot
    """
    try:
        # 1. Verificar identificadores en clientOrderId
        client_order_id = order.get('clientOrderId', '').upper()
        for identifier in BOT_ORDER_IDENTIFIERS:
            if identifier.upper() in client_order_id:
                return True
        
        # 2. Verificar si es un par que usa el bot (obtenemos de la config)
        symbol = order.get('symbol', '')
        if symbol:
            # Intentar obtener configuración actual para validar el par
            try:
                from ..interfaces.telegram_interface import get_dynamic_grid_config
                config = get_dynamic_grid_config()
                bot_pair = config.get('pair', '').replace('/', '')  # ETH/USDT -> ETHUSDT
                
                if symbol == bot_pair:
                    # 3. Verificar características típicas del grid bot
                    # Si es el par correcto y tiene características de grid, probablemente es nuestro
                    return is_grid_like_order(order)
                    
            except Exception:
                pass  # Si no podemos verificar config, seguir con otros criterios
        
        # 4. Verificar patrones típicos de precios del grid bot
        # (precios muy específicos, cantidades calculadas, etc.)
        return is_grid_like_order(order)
        
    except Exception as e:
        logger.debug(f"Error verificando si orden pertenece al bot: {e}")
        return False


def is_grid_like_order(order: Dict[str, Any]) -> bool:
    """
    Verifica si una orden tiene características típicas del grid bot.
    
    Args:
        order: Información de la orden
        
    Returns:
        True si parece una orden del grid bot
    """
    try:
        # Verificar si el precio tiene muchos decimales (típico del grid)
        price = float(order.get('price', 0))
        if price > 0:
            price_str = f"{price:.10f}".rstrip('0')
            decimal_places = len(price_str.split('.')[-1]) if '.' in price_str else 0
            
            # Grid bot suele usar precios muy específicos (más de 2 decimales)
            if decimal_places >= 4:
                return True
        
        # Verificar si la cantidad es muy específica (típico del grid)
        amount = float(order.get('amount', 0))
        if amount > 0:
            amount_str = f"{amount:.10f}".rstrip('0')
            decimal_places = len(amount_str.split('.')[-1]) if '.' in amount_str else 0
            
            # Grid bot suele usar cantidades calculadas (más de 3 decimales)
            if decimal_places >= 5:
                return True
        
        return False
        
    except Exception:
        return False


def send_cleanup_notification(cleanup_result: Dict[str, Any], config: Optional[Dict[str, Any]]) -> None:
    """
    Envía notificación mejorada sobre la limpieza de órdenes al arrancar el servicio.
    
    Args:
        cleanup_result: Resultado de la limpieza
        config: Configuración del bot si estaba disponible
    """
    try:
        if not cleanup_result['exchange_connected']:
            # Si no se pudo conectar, no enviar notificación
            return
        
        message = "🔄 <b>SERVICIO GRID BOT REINICIADO</b>\n\n"
        
        if cleanup_result['success']:
            total_cancelled = cleanup_result['orders_cancelled']
            
            if total_cancelled > 0:
                message += f"🧹 <b>Limpieza automática realizada:</b>\n"
                message += f"• Total órdenes canceladas: <b>{total_cancelled}</b>\n"
                
                if cleanup_result['local_orders_cancelled'] > 0:
                    message += f"  - Locales guardadas: {cleanup_result['local_orders_cancelled']}\n"
                
                if cleanup_result['binance_orders_cancelled'] > 0:
                    message += f"  - Huérfanas en Binance: <b>{cleanup_result['binance_orders_cancelled']}</b> ⚠️\n"
                
                message += f"\n🛡️ <b>Estado actual:</b> EN ESPERA\n"
                message += f"▶️ <b>Para iniciar trading:</b> /start_bot\n"
            else:
                message += f"✅ <b>Sin órdenes pendientes para limpiar</b>\n\n"
                message += f"🛡️ <b>Estado actual:</b> EN ESPERA\n"
                message += f"▶️ <b>Para iniciar trading:</b> /start_bot\n"
        else:
            message += f"⚠️ <b>Limpieza con errores:</b>\n"
            for error in cleanup_result['errors'][:3]:  # Máximo 3 errores
                message += f"• {error}\n"
            message += f"\n🛡️ <b>Estado:</b> EN ESPERA (revisar logs)\n"
        
        if config:
            message += f"\n📊 <b>Configuración anterior:</b>\n"
            message += f"Par: {config.get('pair', 'N/A')} | Capital: ${config.get('total_capital', 0)}\n"
        
        message += f"\n🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de limpieza: {e}")


def initialize_standby_mode() -> bool:
    """
    Inicializa el bot en modo standby (sin iniciar trading automáticamente).
    Solo responde a comandos de Telegram.
    
    Returns:
        True si se inicializó correctamente
    """
    try:
        logger.info("⏸️ ========== INICIALIZANDO MODO STANDBY ==========")
        
        # 1. Realizar limpieza de órdenes huérfanas
        cleanup_result = cleanup_orphaned_orders()
        
        # 2. Verificar que el cleanup fue exitoso
        if not cleanup_result['success']:
            logger.warning("⚠️ Limpieza de órdenes tuvo errores, pero continuando en modo standby")
        
        # 3. Log de estado final
        logger.info("✅ Modo standby activado")
        logger.info("🤖 Bot de Telegram disponible para comandos")
        logger.info("⏸️ Trading NO iniciado automáticamente")
        logger.info("▶️ Usa /start_bot para iniciar trading manual")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando modo standby: {e}")
        return False


def get_standby_status() -> Dict[str, Any]:
    """
    Obtiene el estado actual del modo standby.
    
    Returns:
        Diccionario con información del estado standby
    """
    try:
        from ..schedulers.multibot_scheduler import get_multibot_scheduler
        
        scheduler = get_multibot_scheduler()
        scheduler_running = scheduler and scheduler.scheduler.running
        
        status = scheduler.get_status()
        return {
            'standby_mode': status['total_active_bots'] == 0,
            'scheduler_active': scheduler_running,
            'bot_trading': status['total_active_bots'] > 0,
            'telegram_available': True,  # Siempre disponible si el servicio está activo
            'ready_to_start': scheduler_running and status['total_active_bots'] == 0,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado standby: {e}")
        return {
            'standby_mode': True,
            'scheduler_active': False,
            'bot_trading': False,
            'telegram_available': False,
            'ready_to_start': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


__all__ = [
    'cleanup_orphaned_orders',
    'cleanup_local_saved_orders', 
    'cleanup_binance_orphaned_orders',
    'is_bot_order',
    'is_grid_like_order',
    'send_cleanup_notification',
    'initialize_standby_mode',
    'get_standby_status',
    'CLEANUP_RETRY_ATTEMPTS',
    'CLEANUP_DELAY_SECONDS',
    'BOT_ORDER_IDENTIFIERS'
] 