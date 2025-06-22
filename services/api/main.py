"""
API Gateway - Punto de entrada unificado
Centraliza todos los endpoints de los microservicios de Oráculo Bot.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.api.routers import news_router, grid_router, status_router
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification

logger = get_logger(__name__)

def start_api_gateway():
    """
    Inicia el API Gateway centralizado.
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🌐 Iniciando API Gateway...")
        
        logger.info("✅ API Gateway iniciado correctamente")
        logger.info("📡 Endpoints unificados disponibles")
        logger.info("🔗 Conectando con microservicios")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🌐 API Gateway centralizado",
            "📰 Endpoints de servicio de noticias", 
            "🤖 Endpoints de grid trading",
            "📊 Monitoreo y estado de servicios"
        ]
        send_service_startup_notification("API Gateway", features)
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar API Gateway: {e}")
        raise

def stop_api_gateway():
    """
    Detiene el API Gateway.
    """
    try:
        logger.info("🛑 Deteniendo API Gateway...")
        logger.info("✅ API Gateway detenido correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al detener API Gateway: {e}")

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando aplicación FastAPI del API Gateway...")
    try:
        start_api_gateway()
    except Exception as e:
        logger.error(f"❌ Error al iniciar API Gateway: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando aplicación FastAPI del API Gateway...")
    try:
        stop_api_gateway()
    except Exception as e:
        logger.error(f"❌ Error al detener API Gateway: {e}")

# Aplicación FastAPI principal
app = FastAPI(
    title="Oráculo Bot - API Gateway",
    version="0.1.0",
    description="Gateway centralizado para todos los microservicios de Oráculo Bot",
    lifespan=lifespan
)

# Incluir routers de todos los microservicios
app.include_router(status_router.router, prefix="/api/v1", tags=["Status"])
app.include_router(news_router.router, prefix="/api/v1/news", tags=["News Service"])
app.include_router(grid_router.router, prefix="/api/v1/grid", tags=["Grid Trading"])

# Endpoint raíz del gateway
@app.get("/", tags=["Gateway"])
def read_root():
    """Endpoint principal del API Gateway."""
    return {
        "message": "🌐 Oráculo Bot - API Gateway",
        "status": "operational",
        "services": {
            "news": "📰 Servicio de noticias disponible en /api/v1/news/",
            "grid": "🤖 Grid trading disponible en /api/v1/grid/",
            "status": "📊 Estado general en /api/v1/status"
        },
        "docs": "/docs"
    }

# Endpoint de salud general del gateway
@app.get("/health", tags=["Gateway"])
def health_check():
    """Health check del API Gateway."""
    return {
        "status": "healthy",
        "gateway": "operational",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    # Punto de entrada directo
    try:
        start_api_gateway()
        
        # Mantener el servicio corriendo
        import time
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_api_gateway()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_api_gateway()
        raise 