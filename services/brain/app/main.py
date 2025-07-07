"""
Brain Service - Motor de Decisiones de Trading
==============================================

Servicio principal que implementa el motor de decisiones de trading
siguiendo Clean Architecture y principios SOLID.
"""

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from typing import Dict, Any

# Configuración
from config import get_config, ANALYSIS_INTERVAL, SUPPORTED_PAIRS

# Casos de uso
from application.analyze_pair_use_case import AnalyzePairUseCase
from application.batch_analysis_use_case import BatchAnalysisUseCase
from application.service_lifecycle_use_case import ServiceLifecycleUseCase

# Repositorios
from infrastructure.market_data_repository import BinanceMarketDataRepository
from infrastructure.recipe_repository import InMemoryRecipeRepository
from infrastructure.decision_repository import DatabaseDecisionRepository
from infrastructure.notification_service import HTTPNotificationService
from infrastructure.brain_status_repository import FileBrainStatusRepository

# Configuración de logging
config = get_config()
logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format=config['logging']['format'],
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config['logging']['file'], encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# INSTANCIAS GLOBALES
# ============================================================================

# Repositorios
market_data_repo = BinanceMarketDataRepository()
recipe_repo = InMemoryRecipeRepository()
decision_repo = DatabaseDecisionRepository()
notification_service = HTTPNotificationService()
status_repo = FileBrainStatusRepository(config['files']['status'])

# Casos de uso
analyze_pair_use_case = AnalyzePairUseCase(
    market_data_repo=market_data_repo,
    decision_repo=decision_repo,
    recipe_repo=recipe_repo
)

batch_analysis_use_case = BatchAnalysisUseCase(
    market_data_repo=market_data_repo,
    decision_repo=decision_repo,
    recipe_repo=recipe_repo,
    notification_service=notification_service,
    status_repo=status_repo
)

service_lifecycle_use_case = ServiceLifecycleUseCase(
    status_repo=status_repo,
    notification_service=notification_service
)

# ============================================================================
# LIFECYCLE MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manager del ciclo de vida de la aplicación."""
    # Startup
    try:
        logger.info("🎯 ========== INICIANDO BRAIN SERVICE ==========")
        logger.info("🧠 Brain Service - Motor de Decisiones de Trading (Clean Architecture)")
        logger.info("📋 Configuración:")
        logger.info(f"   📊 Pares soportados: {len(SUPPORTED_PAIRS)}")
        logger.info(f"   🔢 Pares: {', '.join(SUPPORTED_PAIRS)}")
        logger.info(f"   ⏰ Intervalo de análisis: {ANALYSIS_INTERVAL}s")
        logger.info(f"   📁 Log level: {config['logging']['level']}")
        logger.info("🧠 Recetas maestras cargadas para cada par")
        logger.info("🚀 Iniciando servicio brain...")
        
        # Iniciar el servicio brain
        startup_result = await service_lifecycle_use_case.start_service()
        if startup_result['status'] == 'started':
            logger.info("✅ Brain service iniciado correctamente")
        else:
            logger.warning(f"⚠️ Brain service: {startup_result['message']}")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Brain Service: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("🛑 Deteniendo Brain Service...")
        stop_result = await service_lifecycle_use_case.stop_service()
        if stop_result['status'] == 'stopped':
            logger.info("✅ Brain service detenido correctamente")
        else:
            logger.warning(f"⚠️ Brain service: {stop_result['message']}")
        
        # Cerrar servicios
        await notification_service.close()
        
    except Exception as e:
        logger.error(f"❌ Error al detener Brain Service: {e}")

# ============================================================================
# APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="Brain Service - Motor de Decisiones de Trading",
    description="""
    Servicio que actúa como el "cerebro" del sistema de trading.
    
    ## Arquitectura Clean
    
    * **Dominio**: Entidades y reglas de negocio puras
    * **Aplicación**: Casos de uso que orquestan la lógica
    * **Infraestructura**: Implementaciones concretas de repositorios y servicios
    * **Independiente**: No depende de otros servicios para funcionar
    * **Escalable**: Preparado para múltiples tipos de bots
    
    ## Comunicación
    
    * **Base de Datos**: Las decisiones se publican en la tabla `estrategia_status`
    * **Independiente**: Los bots consultan la BD para obtener decisiones
    * **Sin APIs**: No expone endpoints para análisis individual
    * **Preparado para Redis**: Arquitectura lista para comunicación en tiempo real
    
    ## Análisis Automático
    
    * **Frecuencia**: Cada 1 hora
    * **Modo**: Análisis batch de todos los pares simultáneamente
    * **Persistencia**: Decisiones guardadas en base de datos
    * **Notificación**: Preparado para Redis (no implementado aún)
    
    ## Endpoints Disponibles
    
    * **GET /**: Información del servicio
    * **GET /health/**: Health check del servicio (incluye estado del brain)
    """,
    version="1.0.0",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "dev@oraculo-bot.com"
    },
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ENDPOINTS PRINCIPALES
# ============================================================================

@app.get("/")
async def root():
    """
    Endpoint raíz del servicio.
    
    Returns:
        Información básica del servicio
    """
    status_result = await service_lifecycle_use_case.get_service_status()
    
    return {
        "servicio": "Brain - Motor de Decisiones de Trading",
        "version": "1.0.0",
        "arquitectura": "Clean Architecture",
        "estado": "ejecutándose" if status_result.get('is_running') else "detenido",
        "descripcion": "Servicio de análisis continuo independiente que toma decisiones de trading",
        "pares_soportados": SUPPORTED_PAIRS,
        "total_pares": len(SUPPORTED_PAIRS),
        "intervalo_analisis": f"{ANALYSIS_INTERVAL}s",
        "modo": "Análisis continuo independiente",
        "frecuencia": f"Cada {ANALYSIS_INTERVAL}s",
        "analisis_batch": "Activado - todos los pares simultáneamente",
        "comunicacion": "Base de datos - los bots consultan estrategia_status",
        "redis_ready": "Arquitectura preparada para comunicación en tiempo real",
        "endpoints": {
            "health": "/health/",
            "documentacion": "/docs"
        },
        "configuracion": {
            "debug": config['development']['debug'],
            "dev_mode": config['development']['dev_mode'],
            "metrics_enabled": config['monitoring']['metrics_enabled']
        }
    }

@app.get("/health/")
async def health_check():
    """
    Health check del servicio incluyendo estado del brain.
    
    Returns:
        Estado de salud del servicio y estado del brain
    """
    try:
        status_result = await service_lifecycle_use_case.get_service_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "brain",
            "is_running": status_result.get('is_running', False),
            "analysis_task_active": status_result.get('analysis_task_active', False),
            "brain_status": status_result.get('brain_status'),
            "cycle_count": status_result.get('cycle_count', 0),
            "last_analysis_time": status_result.get('last_analysis_time'),
            "total_decisions_processed": status_result.get('total_decisions_processed', 0),
            "successful_decisions": status_result.get('successful_decisions', 0),
            "failed_decisions": status_result.get('failed_decisions', 0)
        }
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        raise HTTPException(status_code=500, detail=f"Error en health check: {str(e)}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def start_brain_service():
    """Función para iniciar el servicio brain."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config['development']['debug'],
        log_level=config['logging']['level'].lower()
    )

if __name__ == "__main__":
    start_brain_service() 