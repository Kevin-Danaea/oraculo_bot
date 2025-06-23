"""
Módulo de gestión de estado y persistencia del Grid Trading Bot.
Maneja guardado/carga de estado, cancelación de órdenes y reset del bot.
"""

import os
import json
import ccxt
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

# Archivo para persistir estado del bot
STATE_FILE = "logs/grid_bot_state.json"


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
            
        active_orders = state.get('active_orders', [])
        config = state.get('config')
        
        logger.info(f"📂 Estado cargado: {len(active_orders)} órdenes activas")
        return active_orders, config
        
    except Exception as e:
        logger.error(f"❌ Error cargando estado: {e}")
        return [], None


def clear_bot_state() -> None:
    """
    Limpia el estado guardado del bot
    """
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            logger.info("🗑️ Estado del bot limpiado")
    except Exception as e:
        logger.error(f"❌ Error limpiando estado: {e}")


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
        except Exception as e:
            logger.error(f"❌ Error cancelando orden {order_info['id']}: {e}")
    
    logger.info(f"✅ Órdenes canceladas: {cancelled_count}/{len(active_orders)}")
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


def force_reset_bot(config: Dict[str, Any]) -> None:
    """
    Fuerza un reset completo del bot (útil para casos de emergencia)
    
    Args:
        config: Configuración del bot
    """
    try:
        logger.warning("🚨 ========== RESET FORZADO DEL BOT ==========")
        
        # Conectar al exchange (necesario importar aquí para evitar dependencia circular)
        from .config_manager import get_exchange_connection
        exchange = get_exchange_connection()
        
        # Cargar órdenes activas
        saved_orders, _ = load_bot_state()
        
        if saved_orders:
            # Cancelar todas las órdenes
            cancelled_orders = cancel_all_active_orders(exchange, saved_orders)
            logger.warning(f"🚫 Reset forzado - Órdenes canceladas: {cancelled_orders}")
        
        # Limpiar estado
        clear_bot_state()
        
        # Notificar
        send_telegram_message("🚨 <b>GRID BOT - RESET FORZADO EJECUTADO</b>\n\n✅ Todas las órdenes han sido canceladas y el estado limpiado.")
        
    except Exception as e:
        logger.error(f"❌ Error en reset forzado: {e}")
        raise


__all__ = [
    'STATE_FILE',
    'save_bot_state',
    'load_bot_state', 
    'clear_bot_state',
    'cancel_all_active_orders',
    'reset_bot_for_new_config',
    'force_reset_bot'
] 