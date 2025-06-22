"""
Router de Status - Endpoints de estado y diagnóstico
Migrado desde app/api/endpoints.py para el nuevo API Gateway.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from services.news.schedulers.news_scheduler import get_news_scheduler
from services.grid.schedulers.grid_scheduler import get_grid_scheduler

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

# --- Endpoints de Estado ---
@router.get("/", tags=["Status"])
def api_status():
    """Endpoint principal para verificar que la API está viva."""
    return {"status": "El Oráculo está vivo y escuchando.", "gateway": "active"}

@router.get("/health", tags=["Status"])
def health_status():
    """Health check detallado de todos los servicios."""
    try:
        services_status = {}
        
        # Verificar servicio de noticias
        try:
            news_scheduler = get_news_scheduler()
            services_status["news"] = {
                "status": "healthy" if news_scheduler and news_scheduler.running else "stopped",
                "scheduler_running": news_scheduler.running if news_scheduler else False
            }
        except Exception as e:
            services_status["news"] = {"status": "error", "error": str(e)}
        
        # Verificar servicio de grid
        try:
            grid_scheduler = get_grid_scheduler()
            services_status["grid"] = {
                "status": "healthy" if grid_scheduler and grid_scheduler.running else "stopped",
                "scheduler_running": grid_scheduler.running if grid_scheduler else False
            }
        except Exception as e:
            services_status["grid"] = {"status": "error", "error": str(e)}
        
        # Estado general
        overall_status = "healthy" if all(
            svc.get("status") == "healthy" for svc in services_status.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "services": services_status,
            "gateway": "operational"
        }
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "gateway": "error"
        }

@router.get("/scheduler", tags=["Status"])
def scheduler_status():
    """
    Endpoint de diagnóstico para verificar el estado de todos los schedulers.
    Migrado desde el endpoint original status_scheduler.
    """
    try:
        all_schedulers = {}
        
        # Scheduler de noticias
        try:
            news_scheduler = get_news_scheduler()
            if news_scheduler and news_scheduler.running:
                news_jobs = []
                for job in news_scheduler.get_jobs():
                    job_data = {
                        "id": job.id,
                        "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    news_jobs.append(job_data)
                
                all_schedulers["news"] = {
                    "status": "running",
                    "jobs": news_jobs,
                    "jobs_count": len(news_jobs)
                }
            else:
                all_schedulers["news"] = {
                    "status": "stopped",
                    "jobs": [],
                    "jobs_count": 0
                }
        except Exception as e:
            all_schedulers["news"] = {
                "status": "error",
                "error": str(e),
                "jobs": [],
                "jobs_count": 0
            }
        
        # Scheduler de grid
        try:
            grid_scheduler = get_grid_scheduler()
            if grid_scheduler and grid_scheduler.running:
                grid_jobs = []
                for job in grid_scheduler.get_jobs():
                    job_data = {
                        "id": job.id,
                        "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    grid_jobs.append(job_data)
                
                all_schedulers["grid"] = {
                    "status": "running",
                    "jobs": grid_jobs,
                    "jobs_count": len(grid_jobs)
                }
            else:
                all_schedulers["grid"] = {
                    "status": "stopped", 
                    "jobs": [],
                    "jobs_count": 0
                }
        except Exception as e:
            all_schedulers["grid"] = {
                "status": "error",
                "error": str(e),
                "jobs": [],
                "jobs_count": 0
            }
        
        # Resumen general
        total_jobs = sum(sch.get("jobs_count", 0) for sch in all_schedulers.values())
        running_schedulers = sum(1 for sch in all_schedulers.values() if sch.get("status") == "running")
        
        return {
            "status": "healthy" if running_schedulers > 0 else "no_schedulers_running",
            "summary": {
                "total_schedulers": len(all_schedulers),
                "running_schedulers": running_schedulers,
                "total_jobs": total_jobs
            },
            "schedulers": all_schedulers
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener estado de schedulers: {e}")
        return {
            "status": "error",
            "error": str(e),
            "schedulers": {}
        } 