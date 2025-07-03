"""
Configuraciones específicas para el servicio Grid.
"""

# Pares de trading soportados (preparado para expansión)
SUPPORTED_PAIRS = [
    'BTC/USDT',
    'ETH/USDT', 
    'AVAX/USDT'
]

# Configuración de trading
MIN_ORDER_VALUE_USDT = 10.0  # Mínimo 10 USDT convertido a cualquier moneda
GRID_LEVELS_DEFAULT = 30
PRICE_RANGE_PERCENT_DEFAULT = 10.0
STOP_LOSS_PERCENT_DEFAULT = 5.0

# Configuración de monitoreo
MONITORING_INTERVAL_HOURS = 1  # Monitoreo cada hora
ORDER_CHECK_TIMEOUT_SECONDS = 30

# Configuración de exchange
EXCHANGE_NAME = 'binance'  # Se puede cambiar en el futuro 