"""
API Gateway - Punto de entrada unificado
Centraliza el monitoreo y health checks de todos los microservicios workers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.api.routers import status_router
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification
from shared.database.session import init_database

logger = get_logger(__name__)

def start_api_gateway():
    """
    Inicia el API Gateway centralizado.
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🌐 Iniciando API Gateway...")
        
        # Inicializar base de datos (crear tablas si no existen)
        logger.info("🗄️ Inicializando base de datos...")
        init_database()
        logger.info("✅ Base de datos inicializada correctamente")
        
        logger.info("✅ API Gateway iniciado correctamente")
        logger.info("📡 Health checks y monitoreo disponibles")
        logger.info("🔗 Conectando con workers: News (8000) + Grid (8001)")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🌐 API Gateway centralizado - Puerto 8002",
            "📊 Health checks agregados de todos los workers", 
            "📰 Monitoreo News Worker (Puerto 8000)",
            "🤖 Monitoreo Grid Worker (Puerto 8001)",
            "🔗 Único punto de entrada HTTP público"
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
    version="2.0.0",
    description="Gateway centralizado para monitoreo de microservicios workers",
    lifespan=lifespan
)

# Incluir router de status/health checks
app.include_router(status_router.router, prefix="/api/v1", tags=["System"])

# Endpoint raíz del gateway
@app.get("/", tags=["Gateway"])
def read_root():
    """Endpoint principal del API Gateway."""
    return {
        "message": "🌐 Oráculo Bot - API Gateway v2.0",
        "architecture": "microservices",
        "status": "operational",
        "workers": {
            "news_worker": "📰 Puerto 8000 - Recolección noticias + análisis sentimientos",
            "grid_worker": "🤖 Puerto 8001 - Grid trading automatizado"
        },
        "monitoring": {
            "health_check": "/api/v1/health - Estado agregado de todos los workers",
            "services_list": "/api/v1/services - Lista de workers disponibles",
            "system_status": "/api/v1/ - Información general del sistema"
        },
        "docs": "/docs"
    }

# Endpoint de salud general del gateway
@app.get("/health", tags=["Gateway"])
def gateway_health():
    """Health check básico del API Gateway (no agrega workers)."""
    return {
        "status": "healthy",
        "gateway": "operational",
        "version": "2.0.0",
        "note": "Para health check completo del sistema usar /api/v1/health"
    }

if __name__ == "__main__":
    # Punto de entrada directo
    try:
        start_api_gateway()
        
        # Mantener el servicio corriendo
        import time
        logger.info("🌐 API Gateway ejecutándose en modo standalone...")
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_api_gateway()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_api_gateway()
        raise 