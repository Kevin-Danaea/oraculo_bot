from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db import session, models
from app.tasks.news_collector import scheduler, run_collection_job
from app.services import cryptopanic_service

# Configurar logging
setup_logging()
logger = get_logger(__name__)

# Crear las tablas en la base de datos al iniciar (si no existen)
models.Base.metadata.create_all(bind=session.engine)

# --- Gestor de Ciclo de Vida de la Aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando la aplicación y el scheduler...")
    try:
        scheduler.start()
        logger.info("✅ Scheduler iniciado correctamente")
    except Exception as e:
        logger.error(f"❌ Error al iniciar el scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando la aplicación...")
    try:
        if scheduler.running:
            logger.info("🔄 Deteniendo el scheduler...")
            scheduler.shutdown(wait=True)
            logger.info("✅ Scheduler detenido correctamente")
        else:
            logger.info("ℹ️ El scheduler ya estaba detenido")
    except Exception as e:
        logger.error(f"❌ Error al detener el scheduler: {e}")
    finally:
        logger.info("👋 Aplicación cerrada")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan
)

# --- Dependencia para la sesión de DB ---
def get_db():
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de la API ---
@app.get("/", tags=["Status"])
def read_root():
    """Endpoint principal para verificar que la API está viva."""
    return {"status": "El Oráculo está vivo y escuchando."}

@app.post("/tasks/trigger-collection", tags=["Tasks"])
def trigger_collection(db: Session = Depends(get_db)):
    """
    Endpoint para disparar manualmente la recolección de noticias.
    Útil para pruebas y debugging.
    """
    logger.info("🚀 Disparando la recolección de noticias manualmente...")
    result = cryptopanic_service.fetch_and_store_posts(db)
    
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
            "message": f"Error en la recolección: {result['error']}",
            "error_details": result["error"]
        }

@app.get("/status_scheduler", tags=["Status"])
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