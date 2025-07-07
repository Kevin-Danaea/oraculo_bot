"""
Caso de uso para obtener eventos de hype recientes.
"""
from typing import List
from app.domain.entities import HypeEvent
from app.domain.interfaces import HypeRepository
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class GetRecentHypeEventsUseCase:
    """
    Este caso de uso recupera los eventos de hype más recientes
    desde el repositorio de datos.
    """
    
    def __init__(self, hype_repository: HypeRepository):
        self.hype_repository = hype_repository

    def execute(self, hours: int, limit: int) -> List[HypeEvent]:
        """
        Ejecuta la consulta para obtener eventos recientes.
        
        Args:
            hours: Ventana de tiempo en horas para buscar eventos.
            limit: Número máximo de eventos a devolver.
            
        Returns:
            Una lista de objetos HypeEvent.
        """
        logger.info(f"🚀 Ejecutando caso de uso: Obtener eventos de hype de las últimas {hours}h (límite: {limit})...")
        
        try:
            events = self.hype_repository.get_recent_events(hours=hours, limit=limit)
            logger.info(f"✅ Se encontraron {len(events)} eventos de hype en la base de datos.")
            return events
        except Exception as e:
            logger.error(f"❌ Error al obtener eventos de hype: {e}", exc_info=True)
            # En un caso de uso de solo lectura, es mejor devolver una lista vacía
            # que lanzar una excepción que pueda romper el flujo del cliente.
            return [] 