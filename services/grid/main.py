"""
Servicio de Grid Trading Bot - Punto de entrada principal
Maneja la ejecución del bot de trading automatizado en Binance.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.grid.schedulers.grid_scheduler import setup_grid_scheduler, get_grid_scheduler, stop_grid_bot_scheduler
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification

logger = get_logger(__name__)

def start_grid_service():
    """
    Inicia el servicio completo de grid trading con todos sus schedulers.
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🤖 Iniciando Servicio de Grid Trading...")
        
        # Configurar e iniciar scheduler
        scheduler = setup_grid_scheduler()
        scheduler.start()
        
        logger.info("✅ Servicio de Grid Trading iniciado correctamente")
        logger.info("🔄 Monitor de salud: Cada 5 minutos")
        logger.info("💹 Trading automatizado: Activo")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🤖 Bot de Grid Trading automatizado",
            "💹 Trading en Binance con estrategia de grilla", 
            "🔄 Monitoreo continuo y recuperación automática",
            "📊 Reportes automáticos por Telegram"
        ]
        send_service_startup_notification("Servicio de Grid Trading", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar servicio de grid trading: {e}")
        raise

def stop_grid_service():
    """
    Detiene el servicio de grid trading y todos sus schedulers.
    """
    try:
        logger.info("🛑 Deteniendo Servicio de Grid Trading...")
        
        # Detener scheduler
        stop_grid_bot_scheduler()
        
        logger.info("✅ Servicio de Grid Trading detenido correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al detener servicio de grid trading: {e}")

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando aplicación FastAPI del Grid Service...")
    try:
        start_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Service: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando aplicación FastAPI del Grid Service...")
    try:
        stop_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Service: {e}")

# Aplicación FastAPI
app = FastAPI(
    title="Oráculo Bot - Grid Trading Service",
    version="0.1.0",
    description="Servicio de Grid Trading automatizado para Binance",
    lifespan=lifespan
)

# Endpoints básicos del servicio
@app.get("/", tags=["Status"])
def read_root():
    """Endpoint principal para verificar que el Grid Service está vivo."""
    return {"status": "Grid Trading Service está vivo y operativo", "service": "grid"}

@app.get("/health", tags=["Status"])
def health_check():
    """Endpoint de health check específico para el grid service."""
    try:
        scheduler = get_grid_scheduler()
        is_running = scheduler.running if scheduler else False
        
        return {
            "status": "healthy" if is_running else "stopped",
            "scheduler_running": is_running,
            "service": "grid"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "service": "grid"
        }

@app.get("/status", tags=["Grid Bot"])
def grid_status():
    """Endpoint para verificar el estado del grid bot."""
    try:
        scheduler = get_grid_scheduler()
        
        if not scheduler or not scheduler.running:
            return {
                "status": "scheduler_stopped",
                "message": "El scheduler del grid bot no está ejecutándose",
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
            "status": "running",
            "message": f"Grid Bot activo con {len(jobs_info)} tareas programadas",
            "jobs": jobs_info,
            "service": "grid"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al obtener el estado del grid bot: {str(e)}",
            "service": "grid"
        }

if __name__ == "__main__":
    # Punto de entrada directo
    try:
        scheduler = start_grid_service()
        
        # Mantener el servicio corriendo
        import time
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_grid_service()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_grid_service()
        raise 