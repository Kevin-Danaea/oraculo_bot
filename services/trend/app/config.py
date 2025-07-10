"""Configuration for Trend Following Bot service."""

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from shared.config.settings import settings


@dataclass
class TrendConfig:
    """Configuración del servicio Trend Following Bot."""
    
    # Database
    database_url: str
    
    # Binance API
    binance_api_key: str
    binance_api_secret: str
    binance_testnet: bool
    
    # Paper Trading API
    paper_trading_api_key: str
    paper_trading_secret_key: str
    
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Trading Configuration
    symbol: str
    capital_allocation: Decimal
    trailing_stop_percent: float
    
    # Service Configuration
    cycle_interval_hours: int = 1
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trend_bot.log"
    
    @classmethod
    def from_env(cls) -> "TrendConfig":
        """Crea la configuración desde variables de entorno."""
        # settings ya está importado arriba
        
        # Obtener símbolo del argumento --pair o variable de entorno
        symbol = os.getenv("TREND_SYMBOL", "BTCUSDT")
        
        # Obtener capital allocation
        capital_str = os.getenv("TREND_CAPITAL_ALLOCATION", "1000")
        capital_allocation = Decimal(capital_str)
        
        # Obtener trailing stop
        trailing_stop = float(os.getenv("TREND_TRAILING_STOP_PERCENT", "5.0"))
        
        return cls(
            # Database
            database_url=settings.DATABASE_URL,
            
            # Binance API
            binance_api_key=settings.BINANCE_API_KEY,
            binance_api_secret=settings.BINANCE_API_SECRET,
            binance_testnet=getattr(settings, 'BINANCE_TESTNET', False),
            
            # Paper Trading API
            paper_trading_api_key=settings.PAPER_TRADING_API_KEY,
            paper_trading_secret_key=settings.PAPER_TRADING_SECRET_KEY,
            
            # Telegram
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID,
            
            # Trading Configuration
            symbol=symbol,
            capital_allocation=capital_allocation,
            trailing_stop_percent=trailing_stop,
            
            # Service Configuration
            cycle_interval_hours=int(os.getenv("TREND_CYCLE_INTERVAL_HOURS", "1")),
            
            # Logging
            log_level=os.getenv("TREND_LOG_LEVEL", "INFO"),
            log_file=os.getenv("TREND_LOG_FILE", "logs/trend_bot.log")
        )


# Instancia global de configuración
_config: Optional[TrendConfig] = None


def get_config() -> TrendConfig:
    """Obtiene la configuración del servicio."""
    global _config
    if _config is None:
        _config = TrendConfig.from_env()
    return _config 