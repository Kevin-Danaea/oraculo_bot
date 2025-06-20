from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.logging_config import get_logger
from app.db import session
from app.tasks.news_collector import scheduler
from app.services import reddit_service

logger = get_logger(__name__)

# Crear el router
router = APIRouter()

# --- Dependencia para la sesión de DB ---
def get_db():
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de la API ---
@router.get("/", tags=["Status"])
def read_root():
    """Endpoint principal para verificar que la API está viva."""
    return {"status": "El Oráculo está vivo y escuchando."}

@router.post("/tasks/trigger-collection", tags=["Tasks"])
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

@router.get("/status_scheduler", tags=["Status"])
def status_scheduler():
    """
    Endpoint de diagnóstico para verificar el estado del scheduler y sus tareas activas.
    Muestra información sobre todas las tareas programadas, incluyendo ID, nombre y próxima ejecución.
    """
    try:
        if not scheduler.running:
            return {
                "status": "scheduler_stopped",
                "message": "El scheduler no está ejecutándose",
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
            "message": f"Scheduler activo con {len(jobs_info)} tareas programadas",
            "jobs": jobs_info
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al obtener el estado del scheduler: {str(e)}",
            "jobs": []
        } 