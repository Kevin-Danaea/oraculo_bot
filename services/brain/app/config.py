"""
Configuración del Brain Service
==============================

Configuración centralizada para el servicio brain.
"""

import os
from typing import Dict, Any

# Configuración de análisis
ANALYSIS_INTERVAL = int(os.getenv('BRAIN_ANALYSIS_INTERVAL', 3600))  # 1 hora en segundos
ANALYSIS_TIMEFRAME = os.getenv('BRAIN_ANALYSIS_TIMEFRAME', '4h')
ANALYSIS_DAYS = int(os.getenv('BRAIN_ANALYSIS_DAYS', 40))

# Configuración de logging
LOG_LEVEL = os.getenv('BRAIN_LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configuración de servicios
GRID_SERVICE_URL = os.getenv('GRID_SERVICE_URL', 'http://grid-service:8000')
TREND_SERVICE_URL = os.getenv('TREND_SERVICE_URL', 'http://trend-service:8000')
DCA_SERVICE_URL = os.getenv('DCA_SERVICE_URL', 'http://dca-service:8000')

# Configuración de base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/oraculo_bot')

# Configuración de Binance
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Configuración de Redis (futuro)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Configuración de LLM (futuro)
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4')

# Configuración de recetas maestras
MASTER_RECIPES = {
    'ETH/USDT': {
        'name': 'Receta Maestra ETH',
        'conditions': {
            'adx_threshold': 30,
            'bollinger_bandwidth_threshold': 0.025,
            'sentiment_threshold': -0.20,
            # Umbrales específicos para TREND
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'grid_config': {
            'price_range_percent': 10.0,
            'grid_levels': 30
        },
        'description': 'Condiciones optimizadas para ETH/USDT basadas en backtesting'
    },
    'BTC/USDT': {
        'name': 'Receta Maestra BTC',
        'conditions': {
            'adx_threshold': 25,
            'bollinger_bandwidth_threshold': 0.035,
            'sentiment_threshold': -0.20,
            # Umbrales específicos para TREND
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'grid_config': {
            'price_range_percent': 7.5,
            'grid_levels': 30
        },
        'description': 'Condiciones optimizadas para BTC/USDT basadas en backtesting'
    },
    'AVAX/USDT': {
        'name': 'Receta Maestra AVAX',
        'conditions': {
            'adx_threshold': 35,
            'bollinger_bandwidth_threshold': 0.020,
            'sentiment_threshold': -0.20,
            # Umbrales específicos para TREND
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'grid_config': {
            'price_range_percent': 10.0,
            'grid_levels': 30
        },
        'description': 'Condiciones optimizadas para AVAX/USDT basadas en backtesting'
    }
}

# Recetas maestras específicas para TREND
TREND_MASTER_RECIPES = {
    'ETH/USDT': {
        'name': 'Receta TREND Maestra ETH',
        'conditions': {
            'adx_threshold': 30,
            'bollinger_bandwidth_threshold': 0.025,
            'sentiment_threshold': -0.20,
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'trend_config': {
            'sma_short_period': 30,
            'sma_long_period': 150,
            'adx_period': 14,
            'sentiment_avg_days': 7,
        },
        'description': 'Receta optimizada para estrategia TREND en ETH/USDT'
    },
    'BTC/USDT': {
        'name': 'Receta TREND Maestra BTC',
        'conditions': {
            'adx_threshold': 25,
            'bollinger_bandwidth_threshold': 0.035,
            'sentiment_threshold': -0.20,
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'trend_config': {
            'sma_short_period': 30,
            'sma_long_period': 150,
            'adx_period': 14,
            'sentiment_avg_days': 7,
        },
        'description': 'Receta optimizada para estrategia TREND en BTC/USDT'
    },
    'AVAX/USDT': {
        'name': 'Receta TREND Maestra AVAX',
        'conditions': {
            'adx_threshold': 35,
            'bollinger_bandwidth_threshold': 0.020,
            'sentiment_threshold': -0.20,
            'adx_trend_threshold': 25.0,
            'sentiment_trend_threshold': -0.1,
        },
        'trend_config': {
            'sma_short_period': 30,
            'sma_long_period': 150,
            'adx_period': 14,
            'sentiment_avg_days': 7,
        },
        'description': 'Receta optimizada para estrategia TREND en AVAX/USDT'
    }
}

# Pares soportados
SUPPORTED_PAIRS = list(MASTER_RECIPES.keys())

# Configuración de notificaciones
NOTIFICATION_TIMEOUT = int(os.getenv('NOTIFICATION_TIMEOUT', 30))
NOTIFICATION_RETRY_ATTEMPTS = int(os.getenv('NOTIFICATION_RETRY_ATTEMPTS', 3))

# Configuración de archivos
STATUS_FILE = os.getenv('BRAIN_STATUS_FILE', 'brain_status.json')
LOG_FILE = os.getenv('BRAIN_LOG_FILE', 'logs/brain_service.log')

# Configuración de monitoreo
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 300))  # 5 minutos
METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'

# Configuración de desarrollo
DEBUG = os.getenv('BRAIN_DEBUG', 'false').lower() == 'true'
DEV_MODE = os.getenv('BRAIN_DEV_MODE', 'false').lower() == 'true'

def get_config() -> Dict[str, Any]:
    """
    Obtiene toda la configuración como diccionario.
    
    Returns:
        Diccionario con toda la configuración
    """
    return {
        'analysis': {
            'interval': ANALYSIS_INTERVAL,
            'timeframe': ANALYSIS_TIMEFRAME,
            'days': ANALYSIS_DAYS
        },
        'logging': {
            'level': LOG_LEVEL,
            'format': LOG_FORMAT,
            'file': LOG_FILE
        },
        'services': {
            'grid': GRID_SERVICE_URL,
            'trend': TREND_SERVICE_URL,
            'dca': DCA_SERVICE_URL
        },
        'database': {
            'url': DATABASE_URL
        },
        'binance': {
            'api_key': BINANCE_API_KEY,
            'api_secret': BINANCE_API_SECRET
        },
        'redis': {
            'url': REDIS_URL
        },
        'llm': {
            'api_key': LLM_API_KEY,
            'model': LLM_MODEL
        },
        'recipes': MASTER_RECIPES,
        'trend_recipes': TREND_MASTER_RECIPES,
        'supported_pairs': SUPPORTED_PAIRS,
        'notifications': {
            'timeout': NOTIFICATION_TIMEOUT,
            'retry_attempts': NOTIFICATION_RETRY_ATTEMPTS
        },
        'files': {
            'status': STATUS_FILE,
            'log': LOG_FILE
        },
        'monitoring': {
            'health_check_interval': HEALTH_CHECK_INTERVAL,
            'metrics_enabled': METRICS_ENABLED
        },
        'development': {
            'debug': DEBUG,
            'dev_mode': DEV_MODE
        }
    } 