from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db import session, models
from app.tasks.news_collector import scheduler as news_scheduler
from app.tasks.grid_bot_scheduler import start_grid_bot_scheduler, stop_grid_bot_scheduler
from app.api.endpoints import router

# Configurar logging
setup_logging()
logger = get_logger(__name__)

# Crear las tablas en la base de datos al iniciar (si no existen)
models.Base.metadata.create_all(bind=session.engine)

# --- Gestor de Ciclo de Vida de la Aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"🚀 Iniciando aplicación en modo: {settings.SERVICE_MODE}")
    
    try:
        # Iniciar servicios según el modo configurado
        if settings.SERVICE_MODE in ["all", "news"]:
            news_scheduler.start()
            logger.info("✅ News Scheduler iniciado correctamente")
        
        if settings.SERVICE_MODE in ["all", "grid"]:
            start_grid_bot_scheduler()
            logger.info("✅ Grid Bot Scheduler iniciado correctamente")
            
    except Exception as e:
        logger.error(f"❌ Error al iniciar schedulers: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando la aplicación...")
    try:
        # Detener servicios
        if settings.SERVICE_MODE in ["all", "news"] and news_scheduler.running:
            logger.info("🔄 Deteniendo news scheduler...")
            news_scheduler.shutdown(wait=True)
            logger.info("✅ News Scheduler detenido correctamente")
        
        if settings.SERVICE_MODE in ["all", "grid"]:
            logger.info("🔄 Deteniendo grid bot scheduler...")
            stop_grid_bot_scheduler()
            logger.info("✅ Grid Bot Scheduler detenido correctamente")
            
    except Exception as e:
        logger.error(f"❌ Error al detener schedulers: {e}")
    finally:
        logger.info("👋 Aplicación cerrada")

app = FastAPI(
    title=f"{settings.PROJECT_NAME} - Modo: {settings.SERVICE_MODE}",
    version="0.1.0",
    lifespan=lifespan
)

# --- Incluir los endpoints solo si no es modo exclusivo de grid ---
if settings.SERVICE_MODE != "grid":
    app.include_router(router) 