"""Configuration for Trend Following Bot service."""

import os
from dataclasses import dataclass
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
    
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Trading Configuration
    default_analysis_timeframe: str = "4h"
    default_confirmation_timeframe: str = "1h"
    min_signal_confidence: float = 0.7
    max_positions_per_symbol: int = 1
    
    # Risk Management
    default_stop_loss_percent: float = 3.0  # 3%
    default_take_profit_percent: float = 9.0  # 9%
    default_trailing_stop_percent: Optional[float] = 2.0  # 2%
    max_position_size_percent: float = 10.0  # 10% del capital
    
    # Service Configuration
    market_analysis_interval_minutes: int = 15
    trade_execution_interval_minutes: int = 5
    position_management_interval_minutes: int = 2
    health_check_interval_minutes: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trend_bot.log"
    
    @classmethod
    def from_env(cls) -> "TrendConfig":
        """Crea la configuración desde variables de entorno."""
        # settings ya está importado arriba
        
        return cls(
            # Database
            database_url=settings.DATABASE_URL,
            
            # Binance API
            binance_api_key=settings.BINANCE_API_KEY,
            binance_api_secret=settings.BINANCE_API_SECRET,
            binance_testnet=getattr(settings, 'BINANCE_TESTNET', False),
            
            # Telegram
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID,
            
            # Trading Configuration (con valores por defecto)
            default_analysis_timeframe=os.getenv(
                "TREND_ANALYSIS_TIMEFRAME", "4h"
            ),
            default_confirmation_timeframe=os.getenv(
                "TREND_CONFIRMATION_TIMEFRAME", "1h"
            ),
            min_signal_confidence=float(os.getenv(
                "TREND_MIN_SIGNAL_CONFIDENCE", "0.7"
            )),
            max_positions_per_symbol=int(os.getenv(
                "TREND_MAX_POSITIONS_PER_SYMBOL", "1"
            )),
            
            # Risk Management
            default_stop_loss_percent=float(os.getenv(
                "TREND_DEFAULT_STOP_LOSS_PERCENT", "3.0"
            )),
            default_take_profit_percent=float(os.getenv(
                "TREND_DEFAULT_TAKE_PROFIT_PERCENT", "9.0"
            )),
            default_trailing_stop_percent=float(os.getenv(
                "TREND_DEFAULT_TRAILING_STOP_PERCENT", "2.0"
            )) if os.getenv("TREND_DEFAULT_TRAILING_STOP_PERCENT") else None,
            max_position_size_percent=float(os.getenv(
                "TREND_MAX_POSITION_SIZE_PERCENT", "10.0"
            )),
            
            # Service Configuration
            market_analysis_interval_minutes=int(os.getenv(
                "TREND_MARKET_ANALYSIS_INTERVAL", "15"
            )),
            trade_execution_interval_minutes=int(os.getenv(
                "TREND_TRADE_EXECUTION_INTERVAL", "5"
            )),
            position_management_interval_minutes=int(os.getenv(
                "TREND_POSITION_MANAGEMENT_INTERVAL", "2"
            )),
            health_check_interval_minutes=int(os.getenv(
                "TREND_HEALTH_CHECK_INTERVAL", "30"
            )),
            
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