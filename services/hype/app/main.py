"""
Punto de entrada para el Servicio de Hype Radar.
Configura la aplicación FastAPI, el ciclo de vida y los endpoints.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

# Importaciones de la aplicación
from app.application.get_recent_hype_events_use_case import GetRecentHypeEventsUseCase
from app.application.service_lifecycle_use_case import ServiceLifecycleUseCase
from app.domain.entities import HypeEvent
from app.infrastructure.database_repository import DatabaseHypeRepository
from app.infrastructure.notification_adapter import TelegramNotificationService
from app.infrastructure.scheduler import HypeScheduler
from app.config import HYPE_SUBREDDITS  # Importar la configuración

# Importaciones compartidas
from shared.database.session import get_db, init_database
from shared.services.logging_config import get_logger, setup_logging

# --- Configuración Inicial ---
setup_logging()
logger = get_logger(__name__)
scheduler: Optional[HypeScheduler] = None


# --- Ciclo de Vida de la Aplicación (Startup y Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    logger.info("🚀 Iniciando ciclo de vida del servicio Hype Radar...")
    
    # Inicializar base de datos
    init_database()
    logger.info("🗄️ Base de datos inicializada.")
    
    # Iniciar scheduler
    db_session = next(get_db())
    scheduler = HypeScheduler(db_session)
    scheduler.start(subreddits_to_scan=HYPE_SUBREDDITS, alert_interval_minutes=5, save_interval_hours=24)
    
    # Notificar inicio
    notification_service = TelegramNotificationService()
    lifecycle_use_case = ServiceLifecycleUseCase(notification_service)
    features = [
        "🎯 Detección de Hype en Reddit",
        "⚡ Escaneo de alertas cada 5 minutos",
        "💾 Guardado histórico cada 24 horas",
        "📊 Resumen diario automático a las 11:00 AM",
        "🚨 Notificaciones de alertas por Telegram"
    ]
    lifecycle_use_case.notify_startup("Servicio de Hype Radar", features)
    
    yield
    
    # Acciones de apagado
    logger.info("🛑 Deteniendo el servicio Hype Radar...")
    if scheduler:
        scheduler.stop()
    logger.info("✅ Servicio Hype Radar detenido correctamente.")


# --- Aplicación FastAPI ---
app = FastAPI(
    title="Oracle Bot - Hype Radar Service",
    description="Servicio para detectar tendencias y hype de criptomonedas en Reddit.",
    version="2.0.0",
    lifespan=lifespan
)


# --- Inyección de Dependencias ---
def get_hype_repository(db: Session = Depends(get_db)) -> DatabaseHypeRepository:
    return DatabaseHypeRepository(db)


# --- Endpoints de la API ---

@app.get("/", tags=["General"])
def read_root():
    """Endpoint raíz para verificar que el servicio está activo."""
    return {"service": "Hype Radar Service", "status": "running"}


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de health check para monitoreo."""
    is_scheduler_running = scheduler.scheduler.running if scheduler and scheduler.scheduler else False
    return {
        "status": "healthy" if is_scheduler_running else "degraded",
        "details": {
            "database": "connected", # Simplificación, se podría verificar la conexión
            "scheduler": "running" if is_scheduler_running else "stopped"
        }
    }

@app.get("/events", response_model=List[HypeEvent], tags=["Hype Events"])
def get_recent_events(
    hours: int = 24,
    limit: int = 50,
    repo: DatabaseHypeRepository = Depends(get_hype_repository)
):
    """
    Obtiene los eventos de hype más recientes registrados en la base de datos.
    """
    use_case = GetRecentHypeEventsUseCase(repo)
    return use_case.execute(hours=hours, limit=limit)

@app.post("/daily-summary", tags=["Reports"])
def send_daily_summary_now(repo: DatabaseHypeRepository = Depends(get_hype_repository)):
    """Envía el resumen diario manualmente (para pruebas)."""
    try:
        from app.application.send_daily_summary_use_case import SendDailySummaryUseCase
        
        use_case = SendDailySummaryUseCase(
            hype_repository=repo,
            notification_service=TelegramNotificationService()
        )
        result = use_case.execute(hours=24)
        
        return {
            "status": "success" if result.get('success', False) else "error",
            **result
        }
    except Exception as e:
        logger.error(f"❌ Error en endpoint de resumen diario: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# INICIO DEL SERVIDOR
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando servidor Hype Radar...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=False,
        log_level="info"
    )
