"""
Endpoints API específicos del servicio de noticias.
Extraídos desde app/api/endpoints.py para funcionalidad de noticias.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.services.logging_config import get_logger
from shared.database import session
from services.news.schedulers.news_scheduler import get_news_scheduler
from services.news.services import reddit_service

logger = get_logger(__name__)

# Crear el router específico para noticias
news_router = APIRouter(prefix="/news", tags=["News"])

# --- Dependencia para la sesión de DB ---
def get_db():
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints específicos de noticias ---
@news_router.post("/trigger-collection")
def trigger_collection(db: Session = Depends(get_db)):
    """
    Endpoint para disparar manualmente la recolección de noticias desde Reddit.
    Útil para pruebas y debugging.
    """
    logger.info("🚀 Disparando la recolección de noticias desde Reddit manualmente...")
    result = reddit_service.fetch_and_store_posts(db)
    
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
            "new_posts": result.get("new_posts", 0),
            "total_posts": result.get("total_posts", 0)
        }
    else:
        # Retorna error HTTP apropiado pero sin romper la API
        return {
            "status": "error",
            "message": f"Error en la recolección desde Reddit: {result['error']}",
            "error_details": result["error"]
        }

@news_router.get("/status")
def news_status():
    """
    Endpoint de diagnóstico para verificar el estado del scheduler de noticias.
    Muestra información sobre las tareas de recolección y análisis de sentimientos.
    """
    try:
        scheduler = get_news_scheduler()
        
        if not scheduler or not scheduler.running:
            return {
                "status": "scheduler_stopped",
                "message": "El scheduler de noticias no está ejecutándose",
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
            "status": "scheduler_running",
            "message": f"Scheduler de noticias activo con {len(jobs_info)} tareas programadas",
            "jobs": jobs_info
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al obtener el estado del scheduler de noticias: {str(e)}",
            "jobs": []
        }

@news_router.get("/")
def news_service_info():
    """
    Información general del servicio de noticias.
    """
    return {
        "service": "News Service",
        "description": "Recopilación de noticias de Reddit y análisis de sentimientos",
        "features": [
            "Recopilación automática cada hora desde Reddit",
            "Análisis de sentimientos cada 4 horas",
            "Filtrado por dominios de noticias confiables",
            "Eliminación de duplicados"
        ],
        "status": "active"
    } 