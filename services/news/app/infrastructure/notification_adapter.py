"""
Adaptador de notificaciones.
Implementación concreta de la interfaz NotificationService.
"""
from typing import List

from app.domain.interfaces import NotificationService
from shared.services.telegram_service import send_service_startup_notification, send_telegram_message
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class TelegramNotificationService(NotificationService):
    """
    Implementación del servicio de notificaciones usando Telegram.
    """
    
    def send_startup_notification(self, service_name: str, features: List[str]) -> None:
        """
        Envía una notificación cuando el servicio se inicia.
        
        Args:
            service_name: Nombre del servicio
            features: Lista de características del servicio
        """
        try:
            send_service_startup_notification(service_name, features)
            logger.info(f"✅ Notificación de inicio enviada para {service_name}")
        except Exception as e:
            logger.error(f"Error enviando notificación de inicio: {e}")
            # No lanzar excepción para no interrumpir el inicio del servicio
    
    def send_error_notification(self, service_name: str, error: str) -> None:
        """
        Envía una notificación cuando ocurre un error.
        
        Args:
            service_name: Nombre del servicio
            error: Descripción del error
        """
        try:
            message = f"❌ ERROR en {service_name}:\n{error}"
            send_telegram_message(message)
            logger.info(f"✅ Notificación de error enviada para {service_name}")
        except Exception as e:
            logger.error(f"Error enviando notificación de error: {e}") 