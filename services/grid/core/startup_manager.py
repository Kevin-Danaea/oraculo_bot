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


def cleanup_orphaned_orders() -> Dict[str, Any]:
    """
    Limpia todas las órdenes huérfanas que puedan haber quedado de sesiones anteriores.
    Se ejecuta automáticamente al reiniciar el servicio.
    
    Returns:
        Diccionario con el resultado de la limpieza
    """
    cleanup_result = {
        'success': False,
        'orders_cancelled': 0,
        'orders_found': 0,
        'errors': [],
        'timestamp': datetime.now().isoformat(),
        'exchange_connected': False
    }
    
    try:
        logger.info("🧹 ========== INICIANDO LIMPIEZA DE ÓRDENES HUÉRFANAS ==========")
        
        # 1. Intentar conectar con el exchange
        try:
            exchange = get_exchange_connection()
            cleanup_result['exchange_connected'] = True
            logger.info("✅ Conexión con exchange establecida")
        except Exception as e:
            logger.error(f"❌ No se pudo conectar al exchange: {e}")
            cleanup_result['errors'].append(f"Exchange connection: {str(e)}")
            return cleanup_result
        
        # 2. Cargar estado previo para obtener órdenes activas
        saved_orders, saved_config = load_bot_state()
        
        if not saved_orders:
            logger.info("ℹ️ No hay órdenes guardadas para limpiar")
            cleanup_result['success'] = True
            return cleanup_result
        
        cleanup_result['orders_found'] = len(saved_orders)
        logger.info(f"🔍 Encontradas {len(saved_orders)} órdenes para verificar")
        
        # 3. Verificar y cancelar órdenes una por una
        cancelled_count = 0
        for order_info in saved_orders:
            try:
                # Verificar si la orden aún está activa
                order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
                
                if order_status['status'] in ['open', 'pending']:
                    # Cancelar orden activa
                    exchange.cancel_order(order_info['id'], order_info['pair'])
                    cancelled_count += 1
                    logger.info(f"🚫 Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
                else:
                    logger.info(f"ℹ️ Orden ya completada: {order_info['id']}")
                    
            except ccxt.OrderNotFound:
                logger.info(f"ℹ️ Orden no encontrada (posiblemente ya ejecutada): {order_info['id']}")
            except Exception as e:
                error_msg = f"Error procesando orden {order_info['id']}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                cleanup_result['errors'].append(error_msg)
        
        # 4. Limpiar estado guardado
        clear_bot_state()
        
        # 5. Preparar resultado
        cleanup_result['orders_cancelled'] = cancelled_count
        cleanup_result['success'] = True
        
        logger.info(f"✅ Limpieza completada: {cancelled_count} órdenes canceladas")
        
        # 6. Enviar notificación de limpieza
        send_cleanup_notification(cleanup_result, saved_config)
        
        return cleanup_result
        
    except Exception as e:
        error_msg = f"Error crítico en limpieza: {str(e)}"
        logger.error(f"❌ {error_msg}")
        cleanup_result['errors'].append(error_msg)
        return cleanup_result


def send_cleanup_notification(cleanup_result: Dict[str, Any], config: Optional[Dict[str, Any]]) -> None:
    """
    Envía notificación sobre la limpieza de órdenes al arrancar el servicio.
    
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
            if cleanup_result['orders_cancelled'] > 0:
                message += f"🧹 <b>Limpieza automática realizada:</b>\n"
                message += f"• Órdenes encontradas: {cleanup_result['orders_found']}\n"
                message += f"• Órdenes canceladas: {cleanup_result['orders_cancelled']}\n\n"
                message += f"🛡️ <b>Estado actual:</b> EN ESPERA\n"
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
        from ..schedulers.grid_scheduler import get_grid_scheduler, grid_bot_running
        
        scheduler = get_grid_scheduler()
        scheduler_running = scheduler and scheduler.running
        
        return {
            'standby_mode': not grid_bot_running,
            'scheduler_active': scheduler_running,
            'bot_trading': grid_bot_running,
            'telegram_available': True,  # Siempre disponible si el servicio está activo
            'ready_to_start': scheduler_running and not grid_bot_running,
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
    'send_cleanup_notification',
    'initialize_standby_mode',
    'get_standby_status',
    'CLEANUP_RETRY_ATTEMPTS',
    'CLEANUP_DELAY_SECONDS'
] 