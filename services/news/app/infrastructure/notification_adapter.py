"""
Adaptador de notificaciones.
Implementación concreta de la interfaz NotificationService.
"""
from typing import List

from app.domain.interfaces import NotificationService
from shared.services import telegram_service
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
            # Formatear mensaje de inicio
            features_text = "\n".join([f"   • {feature}" for feature in features])
            message = f"""
🚀 <b>{service_name}</b> iniciado correctamente

<b>📅 Estado:</b> ✅ Operativo
<b>🎯 Características:</b>
{features_text}

El servicio está listo para procesar solicitudes.
            """.strip()
            
            telegram_service.send_message(message)
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
            message = f"❌ <b>ERROR en {service_name}:</b>\n{error}"
            telegram_service.send_message(message)
            logger.info(f"✅ Notificación de error enviada para {service_name}")
        except Exception as e:
            logger.error(f"Error enviando notificación de error: {e}") 