"""
Servicios compartidos entre microservicios.
Arquitectura limpia con servicios unificados de Telegram.
"""
from .telegram_base import TelegramBaseService, telegram_service
from .telegram_trading import TelegramTradingService, telegram_trading_service
from .logging_config import get_logger

__all__ = [
    # Clases principales
    'TelegramBaseService', 
    'TelegramTradingService',
    
    # Instancias globales
    'telegram_service',
    'telegram_trading_service',
    
    # Utilities
    'get_logger'
] 