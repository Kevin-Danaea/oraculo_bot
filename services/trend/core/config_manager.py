"""
Módulo de gestión de configuración del Trend Trading Bot.
Maneja validación de parámetros y conexiones con el exchange.
"""

import ccxt
from typing import Dict, Any
from shared.services.logging_config import get_logger
from shared.config.settings import settings

logger = get_logger(__name__)


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y normaliza la configuración del trend bot.
    
    Args:
        config: Configuración cruda del bot
        
    Returns:
        Configuración validada y normalizada
        
    Raises:
        ValueError: Si la configuración es inválida
    """
    try:
        # Validar campos requeridos
        required_fields = ['pair', 'total_capital']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Campo requerido faltante: {field}")
        
        # Validar tipos básicos
        pair = str(config['pair']).upper()
        total_capital = float(config['total_capital'])
        
        # Validar capital mínimo
        if total_capital <= 0:
            raise ValueError("El capital total debe ser mayor a 0")
        
        # Capital mínimo recomendado para trend
        min_capital_trend = 500  # USDT mínimo para trend trading
        
        if total_capital < min_capital_trend:
            logger.warning(f"⚠️ Capital bajo para trend trading. Mínimo recomendado: ${min_capital_trend}")
        
        validated_config = {
            'pair': pair,
            'total_capital': total_capital,
            'strategy': 'TREND',
            'min_capital_recommended': min_capital_trend
        }
        
        # Agregar decisión del cerebro si existe
        if 'cerebro_decision' in config:
            validated_config['cerebro_decision'] = config['cerebro_decision']
        
        if 'indicadores' in config:
            validated_config['indicadores'] = config['indicadores']
        
        logger.info(f"✅ Configuración validada:")
        logger.info(f"   📊 Par: {pair}")
        logger.info(f"   💰 Capital: ${total_capital} USDT")
        logger.info(f"   📈 Estrategia: TREND")
        
        return validated_config
        
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        raise


def get_exchange_connection() -> ccxt.Exchange:
    """
    Crea y valida conexión con Binance.
    
    Returns:
        Instancia configurada del exchange
        
    Raises:
        ConnectionError: Si no se puede conectar
    """
    try:
        # Determinar modo (productivo o sandbox)
        # Por defecto usar sandbox para seguridad
        use_sandbox = True  # Siempre usar sandbox por defecto en trend
        
        if use_sandbox:
            api_key = settings.PAPER_TRADING_API_KEY
            api_secret = settings.PAPER_TRADING_SECRET_KEY
            mode_desc = "SANDBOX (Paper Trading)"
        else:
            api_key = settings.BINANCE_API_KEY
            api_secret = settings.BINANCE_API_SECRET
            mode_desc = "PRODUCTIVO (Dinero Real)"
        
        if not api_key or not api_secret:
            raise ConnectionError(f"Las claves API de Binance para modo {mode_desc} no están configuradas")
        
        # Configurar exchange
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'defaultType': 'spot',
            },
            'sandbox': use_sandbox,
            'enableRateLimit': True,
            'timeout': 30000,
        })
        exchange.set_sandbox_mode(use_sandbox)
        
        # Verificar conexión
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        
        logger.info(f"✅ Conexión con Binance establecida - {mode_desc}")
        logger.info(f"💵 Balance USDT disponible: ${usdt_balance:.2f}")
        
        return exchange
        
    except Exception as e:
        logger.error(f"❌ Error conectando con Binance: {e}")
        raise ConnectionError(f"No se pudo conectar con Binance: {e}")


__all__ = [
    'validate_config',
    'get_exchange_connection'
] 