"""
Grid Worker - Servicio de Trading (Pure Worker)
Ejecuta estrategias de grid trading automatizado como background worker.
Expone minimal FastAPI para health checks únicamente.
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
        logger.info("🤖 Iniciando Grid Worker...")
        
        # Configurar e iniciar scheduler
        scheduler = setup_grid_scheduler()
        scheduler.start()
        
        logger.info("✅ Grid Worker iniciado correctamente")
        logger.info("🔄 Monitor de salud: Cada 5 minutos")
        logger.info("💹 Trading automatizado: Activo")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🤖 Bot de Grid Trading automatizado",
            "💹 Trading en Binance con estrategia de grilla", 
            "🔄 Monitoreo continuo y recuperación automática",
            "📊 Reportes automáticos por Telegram",
            "🌐 Health endpoint en puerto 8001"
        ]
        send_service_startup_notification("Grid Worker", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar grid worker: {e}")
        raise

def stop_grid_service():
    """
    Detiene el servicio de grid trading y todos sus schedulers.
    """
    try:
        logger.info("🛑 Deteniendo Grid Worker...")
        
        # Detener scheduler
        stop_grid_bot_scheduler()
        
        logger.info("✅ Grid Worker detenido correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al detener grid worker: {e}")

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando FastAPI del Grid Worker...")
    try:
        start_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Worker: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando FastAPI del Grid Worker...")
    try:
        stop_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Worker: {e}")

# Aplicación FastAPI minimal para health checks
app = FastAPI(
    title="Oráculo Bot - Grid Worker",
    version="0.1.0",
    description="Worker de grid trading automatizado para Binance",
    lifespan=lifespan
)

# Endpoints mínimos para health checks
@app.get("/", tags=["Worker"])
def read_root():
    """Endpoint básico para verificar que el Grid Worker está vivo."""
    return {
        "worker": "grid",
        "status": "alive",
        "description": "Worker de trading - Grid trading automatizado en Binance"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check específico para el grid worker."""
    try:
        scheduler = get_grid_scheduler()
        is_running = scheduler.running if scheduler else False
        
        jobs_count = len(scheduler.get_jobs()) if scheduler and is_running else 0
        
        return {
            "worker": "grid",
            "status": "healthy" if is_running else "stopped",
            "scheduler_running": is_running,
            "active_jobs": jobs_count,
            "features": [
                "🤖 Grid trading strategy",
                "💹 Binance automated trading",
                "🔄 Health monitoring every 5 minutes"
            ]
        }
    except Exception as e:
        return {
            "worker": "grid",
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Punto de entrada directo (sin FastAPI)
    try:
        scheduler = start_grid_service()
        
        # Mantener el servicio corriendo
        import time
        logger.info("🤖 Grid Worker ejecutándose en modo standalone...")
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_grid_service()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_grid_service()
        raise 