from apscheduler.schedulers.background import BackgroundScheduler
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.db import models
from app.services import cryptopanic_service, sentiment_service

logger = get_logger(__name__)

def run_collection_job():
    """
    Tarea que recolecta noticias de CryptoPanic. Se ejecuta cada hora.
    """
    logger.info("Iniciando job de recolección de noticias...")
    db = SessionLocal()
    try:
        cryptopanic_service.fetch_and_store_posts(db)
    finally:
        db.close()
    logger.info("Job de recolección de noticias finalizado.")

def run_sentiment_analysis_job():
    """
    Tarea que busca noticias sin análisis de sentimiento, las procesa y actualiza la BD.
    Se ejecuta cada 4 horas para no saturar la API del LLM.
    """
    logger.info("Iniciando job de análisis de sentimiento...")
    db = SessionLocal()
    try:
        noticias_sin_analizar = db.query(models.Noticia).filter(models.Noticia.sentiment_score == None).limit(60).all() # Limitamos a 60 por ciclo para no exceder cuotas de API
        
        if not noticias_sin_analizar:
            logger.info("No hay noticias nuevas para analizar.")
            return

        logger.info(f"Analizando {len(noticias_sin_analizar)} noticias...")
        for noticia in noticias_sin_analizar:
            score = sentiment_service.analyze_sentiment(str(noticia.headline))
            setattr(noticia, 'sentiment_score', score)
        
        db.commit()
        logger.info("Análisis de sentimiento completado y guardado.")
    finally:
        db.close()

# --- Configuración del Scheduler ---
scheduler = BackgroundScheduler()
# Tarea 1: Recolectar noticias cada hora
scheduler.add_job(run_collection_job, 'interval', hours=1, id='cryptopanic_collector')
# Tarea 2: Analizar sentimiento cada 4 horas
scheduler.add_job(run_sentiment_analysis_job, 'interval', hours=4, id='sentiment_analyzer') 
