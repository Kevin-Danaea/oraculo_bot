"""
Router de News - Endpoints del servicio de noticias
Centraliza todos los endpoints relacionados con recolección y análisis de noticias.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from services.news.services import reddit_service, sentiment_service
from services.news.schedulers.news_scheduler import get_news_scheduler

logger = get_logger(__name__)

# Crear el router
router = APIRouter()

# --- Dependencia para la sesión de DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de Noticias ---
@router.get("/", tags=["News"])
def news_status():
    """Estado general del servicio de noticias."""
    try:
        scheduler = get_news_scheduler()
        is_running = scheduler.running if scheduler else False
        
        return {
            "service": "news",
            "status": "operational" if is_running else "stopped",
            "scheduler_running": is_running,
            "endpoints": {
                "collection": "/trigger-collection",
                "sentiment": "/trigger-sentiment", 
                "status": "/status"
            }
        }
    except Exception as e:
        return {
            "service": "news",
            "status": "error",
            "error": str(e)
        }

@router.post("/trigger-collection", tags=["News"])
def trigger_collection(db: Session = Depends(get_db)):
    """
    Endpoint para disparar manualmente la recolección de noticias desde Reddit.
    Migrado desde app/api/endpoints.py con mejoras.
    """
    logger.info("🚀 Disparando la recolección de noticias desde Reddit manualmente...")
    
    try:
        result = reddit_service.fetch_and_store_posts(db)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "new_posts": result.get("new_posts", 0),
                "total_posts": result.get("total_posts", 0),
                "service": "news"
            }
        else:
            # Retorna error HTTP apropiado pero sin romper la API
            return {
                "status": "error",
                "message": f"Error en la recolección desde Reddit: {result['error']}",
                "error_details": result["error"],
                "service": "news"
            }
    except Exception as e:
        logger.error(f"❌ Error en trigger_collection: {e}")
        return {
            "status": "error",
            "message": f"Error inesperado: {str(e)}",
            "service": "news"
        }

@router.post("/trigger-sentiment", tags=["News"])
def trigger_sentiment_analysis(db: Session = Depends(get_db)):
    """
    Endpoint para disparar manualmente el análisis de sentimientos.
    Nuevo endpoint específico del servicio de noticias.
    """
    logger.info("🧠 Disparando análisis de sentimientos manualmente...")
    
    try:
        result = sentiment_service.analyze_sentiment(db)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "analyzed_posts": result.get("analyzed_posts", 0),
                "service": "news"
            }
        else:
            return {
                "status": "error",
                "message": f"Error en análisis de sentimientos: {result['error']}",
                "error_details": result["error"],
                "service": "news"
            }
    except Exception as e:
        logger.error(f"❌ Error en trigger_sentiment: {e}")
        return {
            "status": "error",
            "message": f"Error inesperado: {str(e)}",
            "service": "news"
        }

@router.get("/status", tags=["News"])
def news_detailed_status():
    """
    Estado detallado del servicio de noticias incluyendo scheduler y jobs.
    """
    try:
        scheduler = get_news_scheduler()
        
        if not scheduler or not scheduler.running:
            return {
                "service": "news",
                "status": "scheduler_stopped",
                "message": "El scheduler del servicio de noticias no está ejecutándose",
                "jobs": []
            }
        
        jobs_info = []
        for job in scheduler.get_jobs():
            job_data = {
                "id": job.id,
                "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            jobs_info.append(job_data)
        
        return {
            "service": "news",
            "status": "running",
            "message": f"Servicio de noticias activo con {len(jobs_info)} tareas programadas",
            "jobs": jobs_info,
            "features": [
                "📰 Recolección automática de Reddit cada hora",
                "🧠 Análisis de sentimientos cada 4 horas",
                "🔍 Filtrado de dominios confiables",
                "📊 Eliminación de duplicados"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener estado detallado de noticias: {e}")
        return {
            "service": "news",
            "status": "error",
            "message": f"Error al obtener el estado: {str(e)}"
        } 