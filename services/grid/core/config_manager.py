"""
Módulo de gestión de configuración y conexiones del Grid Trading Bot.
Maneja validación de parámetros, conexiones con el exchange y reconexiones.
"""

import ccxt
import time
from typing import Dict, Any, Optional
from shared.services.logging_config import get_logger
from shared.config.settings import settings
from ..strategies.grid_strategy import calculate_dynamic_profit_percentage

logger = get_logger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

ORDER_RETRY_ATTEMPTS = 3
RECONNECTION_DELAY = 5  # segundos
MAX_RECONNECTION_ATTEMPTS = 5


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
        
        # Configuración temporal para calcular profit
        temp_config = {
            'price_range_percent': price_range_percent,
            'grid_levels': grid_levels
        }
        dynamic_profit = calculate_dynamic_profit_percentage(temp_config)
        
        validated_config = {
            'pair': pair,
            'total_capital': total_capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range_percent,
            'profit_percentage': dynamic_profit * 100,  # Para logging
            'dynamic_profit_decimal': dynamic_profit,  # Para uso interno
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


def config_has_significant_changes(saved_config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
    """
    Verifica si hay cambios significativos en la configuración que requieran reset
    
    Args:
        saved_config: Configuración guardada
        new_config: Nueva configuración
        
    Returns:
        True si hay cambios significativos
    """
    try:
        # Campos que si cambian requieren reset completo
        critical_fields = ['pair', 'total_capital', 'grid_levels', 'price_range_percent']
        
        for field in critical_fields:
            if saved_config.get(field) != new_config.get(field):
                logger.info(f"🔄 Cambio detectado en {field}: {saved_config.get(field)} → {new_config.get(field)}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error comparando configuraciones: {e}")
        return True  # Por seguridad, resetear si hay error


# Exportar constantes para otros módulos
__all__ = [
    'ORDER_RETRY_ATTEMPTS', 
    'RECONNECTION_DELAY',
    'MAX_RECONNECTION_ATTEMPTS',
    'validate_config',
    'get_exchange_connection',
    'reconnect_exchange',
    'config_has_significant_changes'
] 