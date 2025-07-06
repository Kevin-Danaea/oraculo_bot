"""
Caso de uso para gestionar el ciclo de vida del servicio Grid.
"""
from typing import List

from app.domain.interfaces import NotificationService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class ServiceLifecycleUseCase:
    """
    Gestiona notificaciones del ciclo de vida del servicio Grid.
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        logger.info("✅ ServiceLifecycleUseCase inicializado.")

    def notify_startup(self, service_name: str, features: List[str]) -> None:
        """
        Envía notificación de inicio del servicio.
        
        Args:
            service_name: Nombre del servicio
            features: Lista de características del servicio
        """
        try:
            self.notification_service.send_startup_notification(service_name, features)
            logger.info(f"✅ Notificación de inicio enviada para {service_name}")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {e}")

    def notify_error(self, service_name: str, error: str) -> None:
        """
        Envía notificación de error del servicio.
        
        Args:
            service_name: Nombre del servicio
            error: Descripción del error
        """
        try:
            self.notification_service.send_error_notification(service_name, error)
            logger.info(f"✅ Notificación de error enviada para {service_name}")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}") 