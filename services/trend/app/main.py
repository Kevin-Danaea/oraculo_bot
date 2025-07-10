"""Main entry point for Trend Following Bot service."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from fastapi import FastAPI
import uvicorn

from shared.services.logging_config import setup_logging
from .config import get_config
from .domain.entities import TrendBotConfig
from .application.service_lifecycle_use_case import ServiceLifecycleUseCase
from .infrastructure.brain_directive_repository import DatabaseBrainDirectiveRepository
from .infrastructure.exchange_service import ExchangeService
from .infrastructure.notification_service import NotificationService
from .infrastructure.database_repository import DatabaseTrendBotRepository
from .infrastructure.state_manager import TrendBotStateManager

logger = logging.getLogger(__name__)

# Variables globales para el ciclo de vida
lifecycle_use_case: Optional[ServiceLifecycleUseCase] = None
service_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor del ciclo de vida de la aplicación FastAPI."""
    global lifecycle_use_case, service_running
    
    # Startup
    logger.info("🚀 Iniciando Trend Following Bot con FastAPI...")
    
    try:
        # Configurar logging
        setup_logging()
        
        # Inicializar servicios de infraestructura
        repository = DatabaseTrendBotRepository()
        brain_repository = DatabaseBrainDirectiveRepository()
        exchange_service = ExchangeService()
        notification_service = NotificationService()
        state_manager = TrendBotStateManager(repository)
        
        # Inicializar caso de uso del ciclo de vida multi-pair
        lifecycle_use_case = ServiceLifecycleUseCase(
            repository=repository,
            brain_repository=brain_repository,
            exchange_service=exchange_service,
            notification_service=notification_service,
            state_manager=state_manager,
            telegram_chat_id=get_config().telegram_chat_id
        )
        
        # Iniciar el servicio
        await lifecycle_use_case.start()
        service_running = True
        
        logger.info("✅ Trend Following Bot iniciado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Trend Following Bot: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando Trend Following Bot...")
    
    try:
        if lifecycle_use_case:
            await lifecycle_use_case.stop()
        service_running = False
        logger.info("✅ Trend Following Bot cerrado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al cerrar Trend Following Bot: {e}")


# Crear aplicación FastAPI
app = FastAPI(
    title="Oráculo Bot - Trend Following Service",
    version="2.0.0",
    description="Servicio de trading de tendencias con análisis de mercado y gestión de posiciones",
    lifespan=lifespan
)


@app.get("/", tags=["Status"])
def read_root() -> Dict[str, Any]:
    """Endpoint básico para verificar que el servicio está activo."""
    return {
        "service": "trend-following",
        "version": "2.0.0",
        "status": "alive",
        "description": "Servicio de trading de tendencias - Análisis de mercado y gestión de posiciones"
    }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Health check detallado del servicio."""
    try:
        return {
            "service": "trend-following",
            "status": "healthy" if service_running else "starting",
            "running": service_running,
            "features": [
                "📊 Análisis de mercado multi-timeframe",
                "🎯 Gestión de posiciones con trailing stop",
                "🧠 Integración con Brain para decisiones",
                "💰 Gestión de riesgo táctico",
                "🔄 Sistema multi-pair automático",
                "📱 Notificaciones Telegram"
            ]
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "service": "trend-following",
            "status": "error",
            "error": str(e)
        }


@app.get("/status", tags=["Status"])
def get_service_status() -> Dict[str, Any]:
    """Obtiene el estado detallado del servicio."""
    try:
        if not lifecycle_use_case:
            return {
                "status": "not_initialized",
                "message": "Servicio aún no inicializado"
            }
        
        # Obtener estado del multi-pair manager
        status = lifecycle_use_case.get_status()
        
        return {
            "service": "trend-following",
            "status": "running" if service_running else "stopped",
            "multi_pair_status": status,
            "active_pairs": lifecycle_use_case.multi_pair_manager.get_active_pairs() if lifecycle_use_case else []
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del servicio: {e}")
        return {
            "service": "trend-following",
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# INICIO DEL SERVIDOR
# ============================================================================

if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor Trend Following Bot...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8005,
        reload=False,
        log_level="info"
    ) 