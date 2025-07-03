"""
Caso de uso para manejar el ciclo de vida del servicio.
"""
from ..domain.interfaces import NotificationService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class ServiceLifecycleUseCase:
    """
    Gestiona notificaciones relacionadas con el ciclo de vida del servicio,
    como el inicio o errores críticos.
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    def notify_startup(self, service_name: str, features: list):
        """Notifica que el servicio se ha iniciado correctamente."""
        logger.info(f"🚀 Enviando notificación de inicio para el servicio: {service_name}")
        try:
            self.notification_service.send_startup_notification(service_name, features)
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {e}")

    def notify_error(self, service_name: str, error_message: str):
        """Notifica un error crítico en el servicio."""
        logger.info(f"🔥 Enviando notificación de error para el servicio: {service_name}")
        try:
            self.notification_service.send_error_notification(service_name, error_message)
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}") 