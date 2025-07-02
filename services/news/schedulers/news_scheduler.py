"""
Scheduler principal del servicio de noticias.
Maneja la recolección de Reddit y análisis de sentimientos.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from services.news.services import reddit_service, sentiment_service

logger = get_logger(__name__)

# Instancia global del scheduler
_scheduler = None

def run_news_pipeline_job():
    """
    Tarea unificada que primero recolecta noticias y luego las analiza.
    Se ejecuta cada hora para tener datos de sentimiento casi en tiempo real.
    """
    logger.info("🚀 Iniciando pipeline de noticias: Recolección y Análisis.")
    db = SessionLocal()
    try:
        # Paso 1: Recolectar noticias de Reddit
        logger.info("Iniciando job de recolección de noticias desde Reddit...")
        reddit_service.fetch_and_store_posts(db)
        logger.info("Job de recolección de noticias desde Reddit finalizado.")

        # Paso 2: Analizar sentimientos de las noticias recolectadas
        logger.info("Iniciando job de análisis de sentimiento enriquecido...")
        result = sentiment_service.analyze_sentiment(db)
        if result["success"]:
            logger.info(f"✅ {result['message']}")
        else:
            logger.error(f"❌ Error en análisis de sentimientos: {result.get('error', 'Error desconocido')}")

    except Exception as e:
        logger.error(f"💥 Error inesperado en el pipeline de noticias: {e}")
    finally:
        db.close()
    logger.info("🏁 Pipeline de noticias finalizado.")

def setup_news_scheduler():
    """
    Configura y retorna el scheduler de noticias con una tarea unificada.
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # Tarea Unificada: Recolectar y analizar noticias cada hora
        _scheduler.add_job(
            run_news_pipeline_job, 
            'interval', 
            hours=1, 
            id='news_pipeline',
            name='News Collection and Sentiment Analysis'
        )
        
        logger.info("✅ News scheduler configurado con 1 tarea unificada (recolección + análisis cada hora)")
    
    return _scheduler

def get_news_scheduler():
    """
    Retorna la instancia del scheduler de noticias.
    """
    return _scheduler

def start_news_scheduler():
    """
    Inicia el scheduler de noticias.
    """
    scheduler = setup_news_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ News scheduler iniciado")
    return scheduler

def stop_news_scheduler():
    """
    Detiene el scheduler de noticias.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("✅ News scheduler detenido")
        _scheduler = None 