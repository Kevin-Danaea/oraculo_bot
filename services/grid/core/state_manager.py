"""
Módulo de gestión de estado y persistencia del Grid Trading Bot.
Maneja guardado/carga de estado, cancelación de órdenes y reset del bot.
"""

import os
import json
import ccxt
import glob
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

# Plantilla para los archivos de estado de cada par
STATE_FILE_TEMPLATE = "logs/grid_bot_state_{}.json"

def get_state_file_path(pair: str) -> str:
    """Genera la ruta del archivo de estado para un par específico."""
    pair_slug = pair.replace('/', '-')
    return STATE_FILE_TEMPLATE.format(pair_slug)

def save_bot_state(active_orders: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    """
    Guarda el estado actual del bot en un archivo específico para su par.
    
    Args:
        active_orders: Lista de órdenes activas
        config: Configuración del bot (debe incluir 'pair')
    """
    pair = config.get('pair')
    if not pair:
        logger.error("❌ No se puede guardar estado: 'pair' no encontrado en la configuración.")
        return

    state_file = get_state_file_path(pair)
    
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        state = {
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'active_orders': active_orders,
            'total_orders': len(active_orders)
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        logger.debug(f"💾 Estado guardado para {pair}: {len(active_orders)} órdenes activas")
        
    except Exception as e:
        logger.error(f"❌ Error guardando estado para {pair}: {e}")


def load_bot_state(pair: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Carga el estado previo del bot para un par específico.
    
    Args:
        pair: Par de trading (ej: 'ETH/USDT')
        
    Returns:
        Tuple de (órdenes_activas, configuración) o ([], None) si no existe
    """
    state_file = get_state_file_path(pair)
    
    try:
        if not os.path.exists(state_file):
            return [], None
            
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        # Verificar que no sea muy antiguo (más de 2 días)
        timestamp = datetime.fromisoformat(state['timestamp'])
        if datetime.now() - timestamp > timedelta(days=2):
            logger.warning(f"⚠️ Estado para {pair} muy antiguo, iniciando desde cero")
            return [], None
            
        active_orders = state.get('active_orders', [])
        config = state.get('config')
        
        logger.info(f"📂 Estado cargado para {pair}: {len(active_orders)} órdenes activas")
        return active_orders, config
        
    except Exception as e:
        logger.error(f"❌ Error cargando estado para {pair}: {e}")
        return [], None


def clear_bot_state(pair: str) -> None:
    """Limpia el estado guardado del bot para un par específico."""
    state_file = get_state_file_path(pair)
    try:
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.info(f"🗑️ Estado del bot para {pair} limpiado")
    except Exception as e:
        logger.error(f"❌ Error limpiando estado para {pair}: {e}")

def clear_all_bot_states() -> int:
    """Limpia todos los archivos de estado de todos los bots."""
    try:
        state_files_pattern = get_state_file_path('*')
        state_files = glob.glob(state_files_pattern)
        
        for file_path in state_files:
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"❌ No se pudo eliminar el archivo de estado {file_path}: {e}")
        
        logger.info(f"🗑️ Limpiados {len(state_files)} archivos de estado.")
        return len(state_files)
    except Exception as e:
        logger.error(f"❌ Error limpiando todos los estados: {e}")
        return 0


def cancel_all_active_orders(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]]) -> int:
    """
    Cancela todas las órdenes activas
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes a cancelar
        
    Returns:
        Número de órdenes canceladas exitosamente
    """
    cancelled_count = 0
    
    for order_info in active_orders:
        try:
            exchange.cancel_order(order_info['id'], order_info['pair'])
            cancelled_count += 1
            logger.info(f"🚫 Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
        except ccxt.OrderNotFound:
            logger.info(f"ℹ️ Orden {order_info['id']} no encontrada en el exchange, probablemente ya fue procesada.")
        except Exception as e:
            logger.error(f"❌ Error cancelando orden {order_info['id']}: {e}")
    
    logger.info(f"✅ Órdenes canceladas: {cancelled_count}/{len(active_orders)}")
    return cancelled_count


def reset_bot_for_new_config(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], config: Dict[str, Any], send_notification: bool = True) -> None:
    """
    Resetea completamente el bot para nueva configuración
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas a cancelar
        config: La nueva configuración del bot (para obtener el 'pair')
        send_notification: Si enviar notificación de Telegram (default: True)
    """
    try:
        pair = config.get('pair', 'N/A')
        logger.info(f"🔄 ========== REINICIANDO BOT PARA {pair} CON NUEVA CONFIGURACIÓN ==========")
        
        # 1. Cancelar todas las órdenes activas
        cancelled_orders = cancel_all_active_orders(exchange, active_orders)
        
        # 2. Limpiar estado guardado específico del par
        if pair != 'N/A':
            clear_bot_state(pair)
        
        # 3. Enviar notificación solo si se solicita
        if send_notification:
            message = f"🔄 <b>GRID BOT REINICIADO</b>\n\n"
            message += f"🚫 <b>Órdenes canceladas:</b> {cancelled_orders}\n"
            message += f"🗑️ <b>Estado limpiado:</b> ✅\n"
            message += f"🆕 <b>Iniciando con nueva configuración...</b>"
            
            send_telegram_message(message)
        else:
            logger.info("📱 Notificación de reinicio omitida (modo silencioso)")
        
        logger.info("✅ Reset completado - Bot listo para nueva configuración")
        
    except Exception as e:
        logger.error(f"❌ Error durante el reset del bot: {e}")
        raise


def force_reset_bot(config: Dict[str, Any]) -> None:
    """
    Fuerza un reset completo del bot (útil para casos de emergencia)
    
    Args:
        config: Configuración del bot (debe contener 'pair')
    """
    try:
        pair = config.get('pair')
        if not pair:
            logger.error("❌ Reset forzado falló: 'pair' no encontrado en la configuración.")
            return

        logger.warning(f"🚨 ========== RESET FORZADO DEL BOT PARA {pair} ==========")
        
        # Conectar al exchange (necesario importar aquí para evitar dependencia circular)
        from .config_manager import get_exchange_connection
        exchange = get_exchange_connection()
        
        # Cargar órdenes activas para el par
        saved_orders, _ = load_bot_state(pair)
        
        if saved_orders:
            # Cancelar todas las órdenes
            cancelled_orders = cancel_all_active_orders(exchange, saved_orders)
            logger.warning(f"🚫 Reset forzado - Órdenes canceladas para {pair}: {cancelled_orders}")
        
        # Limpiar estado del par
        clear_bot_state(pair)
        
        # Notificar
        send_telegram_message(f"🚨 <b>GRID BOT - RESET FORZADO EJECUTADO</b>\n\n✅ Todas las órdenes para {pair} han sido canceladas y el estado limpiado.")
        
    except Exception as e:
        logger.error(f"❌ Error en reset forzado: {e}")
        raise


__all__ = [
    'STATE_FILE_TEMPLATE',
    'get_state_file_path',
    'save_bot_state',
    'load_bot_state', 
    'clear_bot_state',
    'clear_all_bot_states',
    'cancel_all_active_orders',
    'reset_bot_for_new_config',
    'force_reset_bot'
] 