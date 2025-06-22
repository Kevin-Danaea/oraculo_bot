"""
News Worker - Servicio de Noticias (Pure Worker)
Recolecta noticias de Reddit y analiza sentimientos como background worker.
Expone minimal FastAPI para health checks únicamente.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.news.schedulers.news_scheduler import setup_news_scheduler, get_news_scheduler, stop_news_scheduler
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
        logger.info("📰 Iniciando News Worker...")
        
        # Configurar e iniciar schedulers
        scheduler = setup_news_scheduler()
        scheduler.start()
        
        logger.info("✅ News Worker iniciado correctamente")
        logger.info("📰 Recopilador de Reddit: Cada hora")
        logger.info("🧠 Análisis de sentimientos: Cada 4 horas")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "📰 Recopilación de Reddit r/CryptoCurrency",
            "🧠 Análisis de sentimientos con Google Gemini", 
            "🔄 Ejecución programada automática",
            "🌐 Health endpoint en puerto 8000"
        ]
        send_service_startup_notification("News Worker", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar news worker: {e}")
        raise

def stop_news_scheduler():
    """
    Detiene el scheduler de noticias.
    """
    try:
        logger.info("🛑 Deteniendo News Worker...")
        
        scheduler = get_news_scheduler()
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ News Worker detenido correctamente")
        else:
            logger.info("ℹ️ El worker ya estaba detenido")
            
    except Exception as e:
        logger.error(f"❌ Error al detener news worker: {e}")

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando FastAPI del News Worker...")
    try:
        start_news_service()
    except Exception as e:
        logger.error(f"❌ Error al iniciar News Worker: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando FastAPI del News Worker...")
    try:
        stop_news_scheduler()
    except Exception as e:
        logger.error(f"❌ Error al detener News Worker: {e}")

# Aplicación FastAPI minimal para health checks
app = FastAPI(
    title="Oráculo Bot - News Worker",
    version="0.1.0",
    description="Worker de recolección de noticias y análisis de sentimientos",
    lifespan=lifespan
)

# Endpoints mínimos para health checks
@app.get("/", tags=["Worker"])
def read_root():
    """Endpoint básico para verificar que el News Worker está vivo."""
    return {
        "worker": "news",
        "status": "alive",
        "description": "Worker de noticias - Recolección Reddit + Análisis sentimientos"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check específico para el news worker."""
    try:
        scheduler = get_news_scheduler()
        is_running = scheduler.running if scheduler else False
        
        jobs_count = len(scheduler.get_jobs()) if scheduler and is_running else 0
        
        return {
            "worker": "news",
            "status": "healthy" if is_running else "stopped",
            "scheduler_running": is_running,
            "active_jobs": jobs_count,
            "features": [
                "📰 Reddit collection every hour",
                "🧠 Sentiment analysis every 4 hours"
            ]
        }
    except Exception as e:
        return {
            "worker": "news",
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Punto de entrada directo (sin FastAPI)
    try:
        scheduler = start_news_service()
        
        # Mantener el servicio corriendo
        import time
        logger.info("📰 News Worker ejecutándose en modo standalone...")
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_news_scheduler()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_news_scheduler()
        raise 