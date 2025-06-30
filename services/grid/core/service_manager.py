"""
Gestor del ciclo de vida del servicio Grid
Centraliza el inicio y parada de todos los componentes
"""

from typing import Any
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification
from shared.database.session import init_database
from services.grid.schedulers.grid_scheduler import (
    start_grid_bot_scheduler, 
    stop_grid_bot_scheduler,
    get_grid_scheduler
)
from services.grid.core.telegram_service import start_telegram_bot, stop_telegram_bot
from services.grid.core.cerebro_integration import obtener_configuracion_trading

logger = get_logger(__name__)

def start_grid_service() -> Any:
    """
    Inicia el servicio completo de grid trading con todos sus componentes.
    
    Returns:
        Scheduler iniciado
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🤖 Iniciando Grid Worker...")
        
        # Mostrar configuración de trading activa
        config = obtener_configuracion_trading()
        logger.info(f"💹 Modo de trading: {config['modo']} - {config['descripcion']}")
        
        # Inicializar base de datos (crear tablas si no existen)
        logger.info("🗄️ Inicializando base de datos...")
        init_database()
        logger.info("✅ Base de datos inicializada correctamente")
        
        # Configurar e iniciar scheduler en modo standby
        start_grid_bot_scheduler()
        scheduler = get_grid_scheduler()
        
        # Iniciar bot de Telegram
        telegram_bot_instance = start_telegram_bot()
        
        # NOTA: La consulta al cerebro se hará en el lifespan de FastAPI
        # para evitar problemas con el event loop
        
        logger.info("✅ Grid Worker iniciado correctamente")
        logger.info("🔄 Monitor de salud: Cada 5 minutos")
        logger.info("💹 Trading automatizado: Activo")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🤖 Bot de Grid Trading automatizado",
            f"💹 Trading en modo: {config['modo']}", 
            "🔄 Monitoreo continuo y recuperación automática",
            "📊 Reportes automáticos por Telegram",
            "🌐 Health endpoint en puerto 8001",
            "🧠 Integración con Cerebro v3.0"
        ]
        
        if telegram_bot_instance:
            features.append("🤖 Bot de Telegram para control remoto")
        
        send_service_startup_notification("Grid Worker", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar grid worker: {e}")
        raise

def stop_grid_service():
    """
    Detiene el servicio de grid trading y todos sus componentes.
    """
    try:
        logger.info("🛑 Deteniendo Grid Worker...")
        
        # Detener bot de Telegram
        stop_telegram_bot()
        
        # Detener scheduler
        stop_grid_bot_scheduler()
        
        logger.info("✅ Grid Worker detenido correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al detener grid worker: {e}")

__all__ = [
    'start_grid_service',
    'stop_grid_service'
] 