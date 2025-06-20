from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db import session, models
from app.tasks.news_collector import scheduler
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

# --- Incluir los endpoints desde el router ---
app.include_router(router) 