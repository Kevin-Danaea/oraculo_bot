"""
Scheduler principal del servicio de noticias.
Maneja la recolección de Reddit y análisis de sentimientos.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from shared.database import models
from services.news.services import reddit_service, sentiment_service

logger = get_logger(__name__)

# Instancia global del scheduler
_scheduler = None

def run_collection_job():
    """
    Tarea que recolecta noticias desde Reddit. Se ejecuta cada hora.
    """
    logger.info("Iniciando job de recolección de noticias desde Reddit...")
    db = SessionLocal()
    try:
        # El servicio de Reddit ahora maneja directamente la BD
        reddit_service.fetch_and_store_posts(db)
    finally:
        db.close()
    logger.info("Job de recolección de noticias desde Reddit finalizado.")

def run_sentiment_analysis_job():
    """
    Tarea que busca noticias sin análisis de sentimiento, las procesa y actualiza la BD.
    Se ejecuta cada 4 horas para no saturar la API del LLM.
    Ahora con análisis enriquecido: sentiment_score, primary_emotion y key_entity.
    """
    logger.info("Iniciando job de análisis de sentimiento enriquecido...")
    db = SessionLocal()
    try:
        # Usar la función del servicio que maneja toda la lógica
        result = sentiment_service.analyze_sentiment(db)
        
        if result["success"]:
            logger.info(f"✅ {result['message']}")
        else:
            logger.error(f"❌ Error en análisis de sentimientos: {result.get('error', 'Error desconocido')}")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job de análisis de sentimiento: {e}")
    finally:
        db.close()
    logger.info("Job de análisis de sentimiento finalizado.")

def setup_news_scheduler():
    """
    Configura y retorna el scheduler de noticias con todas las tareas programadas.
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # Tarea 1: Recolectar noticias cada hora desde Reddit
        _scheduler.add_job(
            run_collection_job, 
            'interval', 
            hours=1, 
            id='reddit_collector',
            name='Reddit News Collection'
        )
        
        # Tarea 2: Analizar sentimiento cada 4 horas
        _scheduler.add_job(
            run_sentiment_analysis_job, 
            'interval', 
            hours=4, 
            id='sentiment_analyzer',
            name='Sentiment Analysis'
        )
        
        logger.info("✅ News scheduler configurado con 2 tareas")
    
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