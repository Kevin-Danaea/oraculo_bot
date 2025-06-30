"""
Grid Worker - Servicio de Trading (Pure Worker)
Ejecuta estrategias de grid trading automatizado como background worker.
Incluye bot de Telegram para control remoto.
Expone minimal FastAPI para health checks únicamente.

INTEGRACIÓN CEREBRO V3.0:
- Consulta estado inicial del Cerebro al arrancar
- Recibe notificaciones automáticas del Cerebro
- Modo productivo vs sandbox controlable desde Telegram
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.services.logging_config import get_logger

# Importar los nuevos módulos organizados
from services.grid.core.service_manager import start_grid_service, stop_grid_service
from services.grid.core.cerebro_integration import (
    MODO_PRODUCTIVO,
    estado_cerebro,
    consultar_estado_inicial_cerebro,
    obtener_configuracion_trading,
    alternar_modo_trading
)

# Importar routers
from services.grid.routers import health_router, cerebro_router, config_router

logger = get_logger(__name__)

# ============================================================================
# LIFESPAN MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan de FastAPI para manejar eventos de inicio y cierre.
    """
    # Evento de inicio
    logger.info("🚀 Iniciando Grid Service...")
    
    # Inicializar el grid service (scheduler, telegram, logs, etc.)
    try:
        scheduler = start_grid_service()
        logger.info("✅ Grid Service iniciado correctamente")
        logger.info("🧠 Grid en MODO AUTÓNOMO - Responde a decisiones del Cerebro")
        logger.info("🔄 Monitoreo automático cada 10 minutos")
        logger.info("📱 Comandos manuales: /start_bot, /stop_bot")
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Service: {e}")
        raise
    
    # NO consultar al cerebro automáticamente - esperar activación manual o automática
    logger.info("🧠 Grid en standby - Consulta al cerebro se hará al activar manualmente o automáticamente")
    
    yield
    
    # Evento de cierre
    logger.info("🛑 Cerrando Grid Service...")
    try:
        stop_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Service: {e}")

# ============================================================================
# APLICACIÓN FASTAPI
# ============================================================================

# Crear aplicación FastAPI con lifespan
app = FastAPI(
    title="Grid Trading Service",
    description="Servicio de Grid Trading con integración Cerebro v3.0",
    version="3.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INCLUIR ROUTERS
# ============================================================================

# Incluir routers organizados
app.include_router(health_router)
app.include_router(cerebro_router)
app.include_router(config_router)

# ============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    # Iniciar el grid service antes de FastAPI
    try:
        logger.info("🚀 Iniciando Grid Service...")
        scheduler = start_grid_service()
        logger.info("✅ Grid Service iniciado correctamente")
        
        # Mantener el servicio corriendo
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

# ============================================================================
# EXPORTAR PARA COMPATIBILIDAD
# ============================================================================

# Exportar variables y funciones para mantener compatibilidad con otros módulos
__all__ = [
    'app',
    'MODO_PRODUCTIVO',
    'estado_cerebro',
    'consultar_estado_inicial_cerebro',
    'obtener_configuracion_trading',
    'alternar_modo_trading'
] 