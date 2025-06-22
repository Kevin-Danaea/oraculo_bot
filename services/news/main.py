"""
Servicio de Noticias - Punto de entrada principal
Maneja la recolección de noticias de Reddit y análisis de sentimientos.
"""
from services.news.schedulers.news_scheduler import setup_news_scheduler, get_news_scheduler
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification

logger = get_logger(__name__)

def start_news_service():
    """
    Inicia el servicio completo de noticias con todos sus schedulers.
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🚀 Iniciando Servicio de Noticias...")
        
        # Configurar e iniciar schedulers
        scheduler = setup_news_scheduler()
        scheduler.start()
        
        logger.info("✅ Servicio de Noticias iniciado correctamente")
        logger.info("📰 Recopilador de Reddit: Cada hora")
        logger.info("🧠 Análisis de sentimientos: Cada 4 horas")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "📰 Recopilación de Reddit r/CryptoCurrency",
            "🧠 Análisis de sentimientos con Google Gemini", 
            "🔄 Ejecución programada automática"
        ]
        send_service_startup_notification("Servicio de Noticias", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar servicio de noticias: {e}")
        raise

def stop_news_service():
    """
    Detiene el servicio de noticias y todos sus schedulers.
    """
    try:
        logger.info("🛑 Deteniendo Servicio de Noticias...")
        
        scheduler = get_news_scheduler()
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Servicio de Noticias detenido correctamente")
        else:
            logger.info("ℹ️ El servicio ya estaba detenido")
            
    except Exception as e:
        logger.error(f"❌ Error al detener servicio de noticias: {e}")

if __name__ == "__main__":
    # Punto de entrada directo
    try:
        scheduler = start_news_service()
        
        # Mantener el servicio corriendo
        import time
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_news_service()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_news_service()
        raise 