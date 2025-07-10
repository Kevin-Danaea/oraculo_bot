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
    
    # Trading Configuration (se obtienen desde BD)
    symbol: str = "ETH/USDT"  # Valor por defecto
    capital_allocation: Decimal = Decimal("300")  # Valor por defecto
    trailing_stop_percent: float = 20.0  # Valor por defecto
    
    # Service Configuration
    cycle_interval_hours: int = 1
    
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
            
            # Paper Trading API
            paper_trading_api_key=settings.PAPER_TRADING_API_KEY,
            paper_trading_secret_key=settings.PAPER_TRADING_SECRET_KEY,
            
            # Telegram
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=settings.TELEGRAM_CHAT_ID,
            
            # Service Configuration
            cycle_interval_hours=int(os.getenv("TREND_CYCLE_INTERVAL_HOURS", "1")),
            
            # Logging
            log_level=os.getenv("TREND_LOG_LEVEL", "INFO"),
            log_file=os.getenv("TREND_LOG_FILE", "logs/trend_bot.log")
        )
    
    async def load_trading_config_from_db(self, telegram_chat_id: str) -> bool:
        """Carga la configuración de trading desde la base de datos."""
        try:
            from shared.database.session import get_db_session
            from shared.database.models import TrendBotConfig
            
            with get_db_session() as session:
                if session is None:
                    return False
                    
                config = session.query(TrendBotConfig).filter(
                    TrendBotConfig.telegram_chat_id == telegram_chat_id,
                    TrendBotConfig.is_active == True
                ).first()
                
                if config:
                    self.symbol = str(config.pair)
                    self.capital_allocation = Decimal(str(config.capital_allocation))
                    self.trailing_stop_percent = float(str(config.trailing_stop_percent))
                    return True
                else:
                    # Usar valores por defecto si no hay configuración
                    return False
                    
        except Exception as e:
            print(f"Error cargando configuración desde BD: {str(e)}")
            return False


# Instancia global de configuración
_config: Optional[TrendConfig] = None


def get_config() -> TrendConfig:
    """Obtiene la configuración del servicio."""
    global _config
    if _config is None:
        _config = TrendConfig.from_env()
    return _config 