"""
Módulo de gestión de estado y persistencia del Trend Trading Bot.
Maneja guardado/carga de estado de posiciones abiertas.
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

# Plantilla para los archivos de estado de cada par
STATE_FILE_TEMPLATE = "logs/trend_bot_state_{}.json"


def get_state_file_path(pair: str) -> str:
    """Genera la ruta del archivo de estado para un par específico."""
    pair_slug = pair.replace('/', '-')
    return STATE_FILE_TEMPLATE.format(pair_slug)


def save_bot_state(pair: str, state: Dict[str, Any]) -> None:
    """
    Guarda el estado actual del bot en un archivo.
    
    Args:
        pair: Par de trading
        state: Estado a guardar
    """
    state_file = get_state_file_path(pair)
    
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        # Agregar timestamp
        state['last_update'] = datetime.now().isoformat()
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        logger.debug(f"💾 Estado guardado para {pair}")
        
    except Exception as e:
        logger.error(f"❌ Error guardando estado para {pair}: {e}")


def load_bot_state(pair: str) -> Optional[Dict[str, Any]]:
    """
    Carga el estado previo del bot para un par específico.
    
    Args:
        pair: Par de trading
        
    Returns:
        Estado guardado o None si no existe
    """
    state_file = get_state_file_path(pair)
    
    try:
        if not os.path.exists(state_file):
            logger.info(f"📂 No hay estado previo para {pair}")
            return None
            
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        logger.info(f"📂 Estado cargado para {pair}")
        
        # Verificar si es un estado válido
        if state.get('position_open', False):
            logger.info(f"📊 Posición abierta encontrada - Entrada: ${state.get('entry_price', 0):.2f}")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ Error cargando estado para {pair}: {e}")
        return None


def clear_bot_state(pair: str) -> None:
    """
    Limpia el estado guardado del bot para un par específico.
    
    Args:
        pair: Par de trading
    """
    state_file = get_state_file_path(pair)
    
    try:
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.info(f"🗑️ Estado del bot para {pair} limpiado")
    except Exception as e:
        logger.error(f"❌ Error limpiando estado para {pair}: {e}")


def update_state_field(pair: str, field: str, value: Any) -> bool:
    """
    Actualiza un campo específico del estado.
    
    Args:
        pair: Par de trading
        field: Campo a actualizar
        value: Nuevo valor
        
    Returns:
        True si se actualizó correctamente
    """
    try:
        # Cargar estado actual
        state = load_bot_state(pair)
        if not state:
            logger.warning(f"⚠️ No hay estado para actualizar en {pair}")
            return False
        
        # Actualizar campo
        state[field] = value
        
        # Guardar estado actualizado
        save_bot_state(pair, state)
        
        logger.debug(f"✅ Campo '{field}' actualizado para {pair}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error actualizando campo '{field}' para {pair}: {e}")
        return False


__all__ = [
    'save_bot_state',
    'load_bot_state',
    'clear_bot_state',
    'update_state_field',
    'get_state_file_path'
] 