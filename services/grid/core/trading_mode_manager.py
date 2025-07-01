"""
Trading Mode Manager
====================

Manages the trading mode of the application (Productive vs. Sandbox)
as a centralized singleton.
"""
from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class _TradingModeManager:
    """
    Manages the productive/sandbox mode state.
    """
    def __init__(self):
        self._is_productive = False  # Default to Sandbox
        logger.info(f"🚀 Trading Mode Manager inicializado en modo: {'PRODUCTIVO' if self._is_productive else 'SANDBOX'}")

    def is_productive(self) -> bool:
        """Returns True if the mode is productive."""
        return self._is_productive

    def toggle_mode(self) -> dict:
        """Toggles the trading mode and returns the new configuration."""
        self._is_productive = not self._is_productive
        new_config = self.get_config()
        logger.info(f"🔄 Modo de trading cambiado a: {new_config['modo']}")
        return new_config

    def get_config(self) -> dict:
        """Returns the configuration for the active trading mode."""
        if self._is_productive:
            return {
                "api_key": settings.BINANCE_API_KEY,
                "api_secret": settings.BINANCE_API_SECRET,
                "modo": "PRODUCTIVO",
                "descripcion": "Trading real en Binance"
            }
        else:
            return {
                "api_key": settings.PAPER_TRADING_API_KEY,
                "api_secret": settings.PAPER_TRADING_SECRET_KEY,
                "modo": "SANDBOX",
                "descripcion": "Paper trading para pruebas"
            }

# Singleton instance of the manager
trading_mode_manager = _TradingModeManager() 