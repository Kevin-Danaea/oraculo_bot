"""
Punto de entrada para el Servicio de Grid Trading Simplificado.
Solo monitorea la base de datos cada hora y ejecuta órdenes.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Optional, Any
from sqlalchemy import text

# Importaciones de la aplicación
from app.application.service_lifecycle_use_case import ServiceLifecycleUseCase
from app.infrastructure.scheduler import GridScheduler
from app.infrastructure.notification_service import TelegramGridNotificationService
from app.infrastructure.telegram_bot import GridTelegramBot
from app.config import SUPPORTED_PAIRS, MONITORING_INTERVAL_HOURS

# Importaciones compartidas
from shared.database.session import get_db, init_database
from shared.services.logging_config import get_logger, setup_logging

# --- Configuración Inicial ---
setup_logging()
logger = get_logger(__name__)
scheduler: Optional[GridScheduler] = None
telegram_bot: Optional[GridTelegramBot] = None


# --- Ciclo de Vida de la Aplicación (Startup y Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler, telegram_bot
    logger.info("🚀 Iniciando ciclo de vida del servicio Grid Trading...")
    
    try:
        # Inicializar base de datos
        init_database()
        logger.info("🗄️ Base de datos inicializada.")
        
                # Inicializar scheduler con sesión de base de datos
        db = next(get_db())
        if db is None:
            raise Exception("No se pudo obtener sesión de base de datos")
        
        scheduler = GridScheduler(db)
        scheduler._setup_jobs(include_realtime=False)  # Solo agenda la gestión horaria
        scheduler.start()
        
        # Inicializar bot de Telegram
        telegram_bot = GridTelegramBot(scheduler)
        telegram_bot.start()
        
        # Inicializar servicios
        notification_service = TelegramGridNotificationService()
        lifecycle_use_case = ServiceLifecycleUseCase(notification_service)
        
        # Realizar limpieza completa al reiniciar
        from app.application.restart_cleanup_use_case import RestartCleanupUseCase
        from app.application.system_integrity_use_case import SystemIntegrityUseCase
        from app.application.trading_status_use_case import TradingStatusUseCase
        
        restart_cleanup_use_case = RestartCleanupUseCase(
            scheduler.grid_repository, 
            scheduler.exchange_service, 
            notification_service
        )
        
        system_integrity_use_case = SystemIntegrityUseCase(
            scheduler.grid_repository,
            scheduler.exchange_service,
            notification_service
        )
        
        trading_status_use_case = TradingStatusUseCase(
            scheduler.grid_repository,
            scheduler.exchange_service,
            notification_service
        )
        
        # Enviar notificación de inicio básica
        features = [
            "🤖 Monitoreo automático de órdenes de grid",
            f"⏰ Verificación cada {MONITORING_INTERVAL_HOURS} hora(s)",
            f"💰 Soporte para pares: {', '.join(SUPPORTED_PAIRS)}",
            "📊 Consulta directa a base de datos (sin Cerebro)",
            "🔄 Creación automática de órdenes complementarias",
            "📱 Comandos básicos por Telegram: start_bot, stop_bot, status",
            "🔒 Verificación de seguridad al reiniciar",
            "📊 Estado detallado de bots y capital"
        ]
        
        lifecycle_use_case.notify_startup("Grid Trading Service", features)
        
        # Realizar limpieza completa al reiniciar
        logger.info("🧹 Iniciando limpieza completa al reiniciar...")
        try:
            cleanup_results = restart_cleanup_use_case.execute()
            
            if cleanup_results['success']:
                logger.info("✅ Limpieza completa exitosa")
                logger.info(f"  📋 Órdenes canceladas: {cleanup_results['orders_cancelled']}")
                logger.info(f"  💰 Activos vendidos: {len(cleanup_results['assets_sold'])}")
                logger.info(f"  💵 USDT recuperado: ${cleanup_results['total_usdt_recovered']:.2f}")
                logger.info(f"  🔄 Bots reseteados: {cleanup_results['bots_reset']}")
            else:
                logger.warning("⚠️ Limpieza completa detectó problemas")
                for error in cleanup_results.get('errors', []):
                    logger.error(f"  ❌ {error}")
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza completa: {e}")
        
        # Realizar validación de integridad
        logger.info("🔍 Iniciando validación de integridad del sistema...")
        try:
            integrity_results = system_integrity_use_case.execute()
            
            if integrity_results['success']:
                logger.info("✅ Validación de integridad exitosa")
            else:
                logger.warning(f"⚠️ Validación de integridad: {integrity_results['overall_status']}")
                for issue in integrity_results.get('issues_found', []):
                    logger.warning(f"  ⚠️ {issue}")
                
        except Exception as e:
            logger.error(f"❌ Error en validación de integridad: {e}")
        
        # 🚀 EJECUTAR GESTIÓN HORARIA INICIAL DESPUÉS DE LA LIMPIEZA
        logger.info("🚀 Iniciando gestión horaria inicial (post-limpieza)...")
        try:
            scheduler.execute_initial_hourly_management()
            logger.info("✅ Gestión horaria inicial completada exitosamente")
        except Exception as e:
            logger.error(f"❌ Error en gestión horaria inicial: {e}")
        
        # Generar estado inicial (sin enviar notificación detallada)
        logger.info("📊 Generando estado inicial...")
        try:
            detailed_status = trading_status_use_case.generate_detailed_status()
            logger.info("✅ Estado inicial generado (notificación detallada deshabilitada)")
        except Exception as e:
            logger.error(f"❌ Error generando estado inicial: {e}")
        
        # 🚦 Activar el monitor en tiempo real solo después de limpieza y gestión horaria
        try:
            scheduler.start_realtime_monitor()
            logger.info("✅ Monitor en tiempo real activado tras limpieza y gestión horaria inicial")
        except Exception as e:
            logger.error(f"❌ Error activando monitor en tiempo real: {e}")
        
        logger.info("✅ Servicio Grid Trading iniciado correctamente")
        for feature in features:
            logger.info(f"  {feature}")
        
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        raise
    
    yield
    
    # Acciones de apagado
    logger.info("🛑 Deteniendo el servicio Grid Trading...")
    try:
        if telegram_bot:
            telegram_bot.stop()
        if scheduler:
            scheduler.stop()
        logger.info("✅ Servicio Grid Trading detenido correctamente.")
    except Exception as e:
        logger.error(f"❌ Error en shutdown: {e}")


# --- Aplicación FastAPI ---
app = FastAPI(
    title="Oracle Bot - Grid Trading Service",
    description="Servicio simplificado de Grid Trading que monitorea la BD cada hora.",
    version="2.0.0",
    lifespan=lifespan
)


# --- Endpoints de la API ---

@app.get("/", tags=["General"])
def read_root():
    """Endpoint raíz para verificar que el servicio está activo."""
    return {
        "service": "Grid Trading Service", 
        "status": "running",
        "supported_pairs": SUPPORTED_PAIRS,
        "monitoring_interval_hours": MONITORING_INTERVAL_HOURS,
        "version": "2.0.0",
        "features": [
            "Monitoreo automático cada hora",
            "Grid trading sin dependencia del Cerebro",
            "Comandos básicos por Telegram",
            "Soporte para múltiples pares de trading"
        ]
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de health check para monitoreo."""
    scheduler_running = False
    telegram_active = False
    
    if scheduler:
        scheduler_running = scheduler.is_running()
    
    if telegram_bot:
        telegram_active = telegram_bot.is_active
    
    try:
        # Verificar conexión a base de datos
        db = next(get_db())
        if db is not None:
            db.execute(text("SELECT 1"))
            db_status = "connected"
        else:
            db_status = "disconnected"
    except Exception:
        db_status = "disconnected"
    
    # Obtener información del exchange si está disponible
    exchange_status = "unknown"
    trading_mode = "unknown"
    if scheduler and hasattr(scheduler, 'exchange_service'):
        try:
            trading_mode = scheduler.exchange_service.get_trading_mode()
            exchange_status = "connected" if scheduler.exchange_service.exchange else "disconnected"
        except:
            exchange_status = "error"
    
    overall_status = "healthy"
    if not scheduler_running or db_status != "connected":
        overall_status = "degraded"
    if exchange_status == "error":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "details": {
            "database": db_status,
            "scheduler": "running" if scheduler_running else "stopped",
            "telegram_bot": "active" if telegram_active else "inactive",
            "exchange": exchange_status,
            "trading_mode": trading_mode,
            "supported_pairs": len(SUPPORTED_PAIRS),
            "monitoring_interval": f"{MONITORING_INTERVAL_HOURS}h"
        },
        "scheduler_info": scheduler.get_status() if scheduler else None
    }


@app.post("/telegram/command", tags=["Telegram"])
def handle_telegram_command(command: str):
    """Endpoint para manejar comandos de Telegram (para testing)."""
    if not telegram_bot:
        return {"status": "error", "message": "Bot de Telegram no disponible"}
    
    try:
        response = telegram_bot.handle_command(command)
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"❌ Error procesando comando: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/manual-monitor", tags=["Operations"])
def trigger_manual_monitor():
    """Endpoint para ejecutar monitoreo manual."""
    if not scheduler:
        return {"status": "error", "message": "Scheduler no disponible"}
    
    try:
        result = scheduler.trigger_manual_monitoring()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"❌ Error en monitoreo manual: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# INICIO DEL SERVIDOR
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando servidor Grid Trading...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    ) 