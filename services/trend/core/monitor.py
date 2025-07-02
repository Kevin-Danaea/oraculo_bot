"""
Monitor del Trend Trading Bot.
Como el trend bot es dirigido por el cerebro, no necesita un monitor continuo.
"""

from typing import Dict, Any
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


def monitor_trend_position(exchange, state: Dict[str, Any], config: Dict[str, Any]) -> None:
    """
    Monitor placeholder para el trend bot.
    El monitoreo real se hace en el scheduler que consulta al cerebro periódicamente.
    
    Args:
        exchange: Instancia del exchange
        state: Estado de la posición
        config: Configuración del bot
    """
    logger.info("📊 Monitor de trend - El cerebro controla las decisiones")
    # El trend bot no necesita monitoreo continuo como el grid bot
    # Las decisiones vienen del cerebro cada hora
    pass


__all__ = ['monitor_trend_position'] 