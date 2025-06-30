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
    Valida y normaliza la configuración del grid bot con parámetros fijos optimizados.
    
    PARÁMETROS FIJOS (validados por backtesting):
    - 30 niveles de grid
    - 10% de rango de precios
    - Solo se valida el capital mínimo necesario en modo productivo
    
    Args:
        config: Configuración cruda del bot
        
    Returns:
        Configuración validada y normalizada con parámetros fijos
        
    Raises:
        ValueError: Si la configuración es inválida
    """
    try:
        # Importar aquí para evitar dependencia circular
        from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
        
        # Validar campos requeridos
        required_fields = ['pair', 'total_capital']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Campo requerido faltante: {field}")
        
        # Validar tipos básicos
        pair = str(config['pair']).upper()
        total_capital = float(config['total_capital'])
        
        # PARÁMETROS FIJOS OPTIMIZADOS (no configurables)
        grid_levels = 30  # Validado por backtesting
        price_range_percent = 10.0  # Validado por backtesting
        
        # Validar capital mínimo necesario SOLO en modo productivo
        if total_capital <= 0:
            raise ValueError("El capital total debe ser mayor a 0")
        
        if MODO_PRODUCTIVO:
            # Calcular capital mínimo considerando comisiones y seguridad
            # Estimación: cada nivel necesita ~$25-30 USDT para cubrir:
            # - Comisiones de Binance (0.1% por trade)
            # - Spread entre compra/venta
            # - Fluctuaciones del 10% de rango
            # - Liquidez para recompras
            capital_minimo_por_nivel = 25  # USDT por nivel
            capital_minimo_requerido = grid_levels * capital_minimo_por_nivel  # 30 * 25 = $750
            
            if total_capital < capital_minimo_requerido:
                raise ValueError(
                    f"Capital insuficiente. Para {grid_levels} niveles con {price_range_percent}% de rango "
                    f"se requiere mínimo ${capital_minimo_requerido} USDT. "
                    f"Capital actual: ${total_capital} USDT"
                )
        else:
            # Modo sandbox - usar valores fijos
            capital_minimo_por_nivel = 25  # Para cálculos internos
            capital_minimo_requerido = 1000.0  # Capital fijo para sandbox
            logger.info("🟡 Modo SANDBOX: Usando capital fijo de $1000 USDT")
        
        # Configuración temporal para calcular profit
        temp_config = {
            'price_range_percent': price_range_percent,
            'grid_levels': grid_levels
        }
        dynamic_profit = calculate_dynamic_profit_percentage(temp_config)
        
        validated_config = {
            'pair': pair,
            'total_capital': total_capital,
            'grid_levels': grid_levels,  # Fijo: 30
            'price_range_percent': price_range_percent,  # Fijo: 10%
            'profit_percentage': dynamic_profit * 100,  # Para logging
            'dynamic_profit_decimal': dynamic_profit,  # Para uso interno
            'max_orders_per_side': grid_levels // 2 + 1,
            'min_order_size': total_capital * 0.001,  # 0.1% del capital mínimo por orden
            'capital_minimo_por_nivel': capital_minimo_por_nivel,
            'capital_minimo_requerido': capital_minimo_requerido
        }
        
        modo_desc = "PRODUCTIVO" if MODO_PRODUCTIVO else "SANDBOX"
        logger.info(f"✅ Configuración validada con parámetros fijos ({modo_desc}):")
        logger.info(f"   📊 Par: {pair}")
        logger.info(f"   💰 Capital: ${total_capital} USDT")
        logger.info(f"   🎯 Niveles: {grid_levels} (fijo)")
        logger.info(f"   📈 Rango: {price_range_percent}% (fijo)")
        logger.info(f"   💹 Profit dinámico: {dynamic_profit*100:.2f}%")
        
        return validated_config
        
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        raise


def get_exchange_connection() -> ccxt.Exchange:
    """
    Crea y valida conexión con Binance (productivo o sandbox según modo)
    
    Returns:
        Instancia configurada del exchange
        
    Raises:
        ConnectionError: Si no se puede conectar
    """
    try:
        # Importar aquí para evitar dependencia circular
        from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
        
        if MODO_PRODUCTIVO:
            # Modo productivo - usar credenciales reales
            api_key = settings.BINANCE_API_KEY
            api_secret = settings.BINANCE_API_SECRET
            sandbox_mode = False
            modo_desc = "PRODUCTIVO (dinero real)"
        else:
            # Modo sandbox - usar credenciales de paper trading
            api_key = settings.PAPER_TRADING_API_KEY
            api_secret = settings.PAPER_TRADING_SECRET_KEY
            sandbox_mode = True
            modo_desc = "SANDBOX (paper trading)"
        
        if not api_key or not api_secret:
            raise ConnectionError(f"Las claves API de Binance para modo {modo_desc} no están configuradas")
        
        # Configurar exchange
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': sandbox_mode,
            'enableRateLimit': True,
            'timeout': 30000,  # 30 segundos timeout
            'rateLimit': 1200,  # ms entre requests
        })
        
        # Verificar conexión y permisos
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        
        logger.info(f"✅ Conexión con Binance establecida - {modo_desc}")
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
    Verifica si hay cambios significativos en la configuración que requieran reset.
    
    CAMBIOS SIGNIFICATIVOS (solo par y capital):
    - Par de trading
    - Capital total
    
    Los parámetros técnicos (niveles, rango) son fijos y no se consideran cambios.
    
    Args:
        saved_config: Configuración guardada
        new_config: Nueva configuración
        
    Returns:
        True si hay cambios significativos
    """
    try:
        # Solo campos que si cambian requieren reset completo
        # Los parámetros técnicos (grid_levels, price_range_percent) son fijos
        critical_fields = ['pair', 'total_capital']
        
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