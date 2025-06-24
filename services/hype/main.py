"""
Hype Radar Worker - Detector de Tendencias de Memecoins (Pure Worker)
=====================================================================

Monitorea subreddits de alto riesgo y detecta menciones frecuentes de memecoins/altcoins
que podrían indicar pumps inminentes. Expone minimal FastAPI para health checks únicamente.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.hype.schedulers.hype_scheduler import setup_hype_scheduler, get_hype_scheduler, stop_hype_scheduler
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification
from shared.database.session import init_database

logger = get_logger(__name__)

def start_hype_service():
    """
    Inicia el servicio completo del hype radar con todos sus schedulers.
    """
    try:
        # Configurar logging
        setup_logging()
        logger.info("🎯 Iniciando Hype Radar Worker...")
        
        # Inicializar base de datos (crear tablas si no existen)
        logger.info("🗄️ Inicializando base de datos...")
        init_database()
        
        # Verificar que la tabla HypeEvent funciona correctamente
        try:
            from shared.database.session import SessionLocal
            from shared.database.models import HypeEvent
            
            db = SessionLocal()
            try:
                # Hacer una consulta simple para verificar que la tabla existe
                count = db.query(HypeEvent).count()
                logger.info(f"💾 Tabla 'hype_events' verificada correctamente ({count} eventos existentes)")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"⚠️ Error verificando tabla hype_events: {e}")
        
        logger.info("✅ Base de datos inicializada correctamente")
        
        # Configurar e iniciar schedulers
        scheduler = setup_hype_scheduler()
        scheduler.start()
        
        logger.info("✅ Hype Radar Worker iniciado correctamente")
        logger.info("🎯 Escaneo de tendencias: Cada hora")
        logger.info("📡 Monitoreando 9 subreddits de alto riesgo")
        
        # Enviar notificación de inicio con características específicas
        features = [
            "🎯 Detección de tendencias de memecoins/altcoins",
            "📡 Monitoreo de 9 subreddits de alto riesgo",
            "🔍 Análisis de ~45+ tickers populares",
            "⏰ Escaneos cada hora con ventana de 1h",
            "🌐 Health endpoint en puerto 8000"
        ]
        send_service_startup_notification("Hype Radar Worker", features)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar hype radar worker: {e}")
        raise

def stop_hype_service():
    """
    Detiene el scheduler del hype radar.
    """
    try:
        logger.info("🛑 Deteniendo Hype Radar Worker...")
        
        scheduler = get_hype_scheduler()
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Hype Radar Worker detenido correctamente")
        else:
            logger.info("ℹ️ El worker ya estaba detenido")
            
    except Exception as e:
        logger.error(f"❌ Error al detener hype radar worker: {e}")

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando FastAPI del Hype Radar Worker...")
    try:
        start_hype_service()
    except Exception as e:
        logger.error(f"❌ Error al iniciar Hype Radar Worker: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando FastAPI del Hype Radar Worker...")
    try:
        stop_hype_service()
    except Exception as e:
        logger.error(f"❌ Error al detener Hype Radar Worker: {e}")

# Aplicación FastAPI minimal para health checks
app = FastAPI(
    title="Oráculo Bot - Hype Radar Worker",
    version="1.0.0",
    description="Worker de detección de tendencias de memecoins y altcoins en subreddits de alto riesgo",
    lifespan=lifespan
)

# Endpoints mínimos para health checks
@app.get("/", tags=["Worker"])
def read_root():
    """Endpoint básico para verificar que el Hype Radar Worker está vivo."""
    return {
        "worker": "hype_radar",
        "status": "alive",
        "description": "Detector de tendencias - Monitoreo de memecoins en subreddits de alto riesgo"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check específico para el hype radar worker."""
    try:
        scheduler = get_hype_scheduler()
        is_running = scheduler.running if scheduler else False
        
        jobs_count = len(scheduler.get_jobs()) if scheduler and is_running else 0
        
        return {
            "worker": "hype_radar",
            "status": "healthy" if is_running else "stopped",
            "scheduler_running": is_running,
            "active_jobs": jobs_count,
            "monitoring_features": [
                "🎯 9 subreddits de alto riesgo",
                "🔍 ~45+ tickers populares",
                "⏰ Escaneos cada hora"
            ],
            "subreddits_monitored": [
                "SatoshiStreetBets", "CryptoMoonShots", "CryptoCurrencyTrading",
                "altcoin", "CryptoHorde", "CryptoBets", "CryptoPumping"
            ]
        }
    except Exception as e:
        return {
            "worker": "hype_radar",
            "status": "error",
            "error": str(e)
        }

@app.get("/status", tags=["Status"])
def get_status():
    """Endpoint para obtener información detallada del estado del hype radar."""
    try:
        from services.hype.services.hype_radar_service import HYPE_SUBREDDITS, TARGET_TICKERS
        
        scheduler = get_hype_scheduler()
        is_running = scheduler.running if scheduler else False
        
        return {
            "service": "hype_radar",
            "version": "1.0.0",
            "status": "running" if is_running else "stopped",
            "configuration": {
                "subreddits_count": len(HYPE_SUBREDDITS),
                "target_tickers_count": len(TARGET_TICKERS),
                "scan_frequency": "every_hour",
                "time_window": "1_hour"
            },
            "subreddits": HYPE_SUBREDDITS,
            "sample_tickers": TARGET_TICKERS[:10]  # Mostrar solo los primeros 10
        }
    except Exception as e:
        return {
            "service": "hype_radar",
            "status": "error",
            "error": str(e)
        }

@app.get("/trends", tags=["Analytics"])
def get_trending_summary(hours: int = 24):
    """Endpoint para obtener un resumen de las tendencias detectadas."""
    try:
        from services.hype.services.hype_radar_service import get_hype_trends_summary
        
        result = get_hype_trends_summary(hours)
        
        if result.get('success', False):
            return {
                "status": "success",
                "hours_analyzed": hours,
                "summary": result['summary']
            }
        else:
            return {
                "status": "error",
                "error": result.get('error', 'Error desconocido')
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/configure", tags=["Configuration"])
def configure_hype_threshold(threshold: float = 500.0):
    """Endpoint para configurar el umbral de alertas de hype."""
    try:
        from services.hype.services.hype_radar_service import configure_hype_alerts
        
        result = configure_hype_alerts(threshold)
        
        return {
            "status": "success" if result.get('success', False) else "error",
            **result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/events", tags=["Database"])
def get_hype_events(hours: int = 24, limit: int = 50):
    """Endpoint para obtener eventos de hype registrados en la base de datos."""
    try:
        from services.hype.core.notifications import get_recent_hype_events
        
        events = get_recent_hype_events(hours, limit)
        
        return {
            "status": "success",
            "hours_searched": hours,
            "events_found": len(events),
            "events": events
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/alerts/test", tags=["Testing"])
def test_alert_system():
    """Endpoint para probar el sistema de alertas."""
    try:
        from services.hype.core.notifications import send_system_alert
        
        success = send_system_alert(
            "🧪 Test del sistema de alertas del Hype Radar\n" +
            "Si recibes este mensaje, las alertas están funcionando correctamente.",
            "INFO"
        )
        
        return {
            "status": "success" if success else "error",
            "message": "Alerta de prueba enviada" if success else "Error enviando alerta de prueba"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Punto de entrada directo (sin FastAPI)
    try:
        scheduler = start_hype_service()
        
        # Mantener el servicio corriendo
        import time
        logger.info("🎯 Hype Radar Worker ejecutándose en modo standalone...")
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_hype_service()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_hype_service()
        raise 