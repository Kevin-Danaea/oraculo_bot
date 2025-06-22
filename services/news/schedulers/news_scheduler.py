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
    """
    logger.info("Iniciando job de análisis de sentimiento...")
    db = SessionLocal()
    try:
        noticias_sin_analizar = db.query(models.Noticia).filter(
            models.Noticia.sentiment_score == None
        ).limit(60).all()  # Limitamos a 60 por ciclo para no exceder cuotas de API
        
        if not noticias_sin_analizar:
            logger.info("No hay noticias nuevas para analizar.")
            return

        logger.info(f"Analizando {len(noticias_sin_analizar)} noticias...")
        for noticia in noticias_sin_analizar:
            score = sentiment_service.analyze_sentiment_text(str(noticia.headline))
            setattr(noticia, 'sentiment_score', score)
        
        db.commit()
        logger.info("Análisis de sentimiento completado y guardado.")
    finally:
        db.close()

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