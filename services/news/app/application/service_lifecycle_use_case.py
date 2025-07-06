"""
Caso de uso para gestionar el ciclo de vida del servicio.
"""
from app.domain.interfaces import NotificationService
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class ServiceLifecycleUseCase:
    """
    Caso de uso para gestionar el ciclo de vida del servicio.
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
    
    def notify_startup(self) -> None:
        """Notifica que el servicio se ha iniciado."""
        features = [
            "📰 Recopilación de Reddit desde múltiples subreddits crypto",
            "🧠 Análisis enriquecido con Google Gemini (score + emoción + categoría)",
            "🔄 Pipeline unificado de recolección y análisis cada hora",
            "🌐 Health endpoint en puerto 8000"
        ]
        
        try:
            self.notification_service.send_startup_notification(
                "News Worker",
                features
            )
            logger.info("✅ Notificación de inicio enviada")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {e}")
    
    def notify_error(self, error: str) -> None:
        """Notifica que ha ocurrido un error."""
        try:
            self.notification_service.send_error_notification(
                "News Worker",
                error
            )
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}") 