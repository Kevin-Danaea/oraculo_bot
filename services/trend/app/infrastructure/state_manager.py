"""State manager for trend bot."""

import logging
from typing import Optional

from ..domain.entities import TrendBotStatus, TrendBotConfig, TrendBotState
from ..domain.interfaces import ITrendBotStateManager, ITrendBotRepository

logger = logging.getLogger(__name__)


class TrendBotStateManager(ITrendBotStateManager):
    """Gestor de estado del trend bot."""
    
    def __init__(self, repository: ITrendBotRepository):
        self.repository = repository
        logger.info("✅ TrendBotStateManager inicializado")
    
    async def initialize_state(
        self, 
        bot_id: str, 
        config: TrendBotConfig
    ) -> TrendBotStatus:
        """Inicializa el estado del bot."""
        try:
            # Crear estado inicial
            status = TrendBotStatus(
                bot_id=bot_id,
                symbol=config.symbol,
                state=TrendBotState.FUERA_DEL_MERCADO,
                current_position=None,
                last_decision=None
            )
            
            # Guardar estado
            await self.repository.save_bot_status(status)
            
            logger.info(f"✅ Estado inicializado para bot {bot_id}")
            return status
            
        except Exception as e:
            logger.error(f"Error inicializando estado: {str(e)}")
            raise
    
    async def update_state(self, status: TrendBotStatus) -> None:
        """Actualiza el estado del bot."""
        try:
            await self.repository.save_bot_status(status)
            logger.debug(f"Estado actualizado para bot {status.bot_id}")
            
        except Exception as e:
            logger.error(f"Error actualizando estado: {str(e)}")
            raise
    
    async def get_state(self, bot_id: str) -> Optional[TrendBotStatus]:
        """Obtiene el estado actual del bot."""
        try:
            return await self.repository.get_bot_status(bot_id)
            
        except Exception as e:
            logger.error(f"Error obteniendo estado: {str(e)}")
            return None
    
    async def save_state(self, status: TrendBotStatus) -> None:
        """Guarda el estado del bot."""
        try:
            await self.repository.save_bot_status(status)
            
        except Exception as e:
            logger.error(f"Error guardando estado: {str(e)}")
            raise 