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
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
from services.grid.schedulers.grid_scheduler import get_grid_scheduler, stop_grid_bot_scheduler
from shared.services.logging_config import setup_logging, get_logger
from shared.services.telegram_service import send_service_startup_notification
from shared.database.session import init_database

# Imports para el bot de Telegram
from shared.services.telegram_bot_service import TelegramBot
from services.grid.interfaces.telegram_interface import GridTelegramInterface

logger = get_logger(__name__)

# Variables globales para el bot de Telegram
telegram_bot = None
telegram_interface = None
telegram_thread = None

# ============================================================================
# INTEGRACIÓN CON CEREBRO V3.0
# ============================================================================

# Variable global para controlar modo productivo/sandbox
MODO_PRODUCTIVO = True  # True = Productivo, False = Sandbox/Paper Trading

# Estado de la decisión del cerebro
estado_cerebro = {
    "decision": "PAUSAR_GRID",  # Por defecto pausado hasta consultar cerebro
    "ultima_actualizacion": None,
    "fuente": "inicial"
}

class DecisionCerebro(BaseModel):
    """Modelo para recibir decisiones del Cerebro"""
    par: str
    decision: str  # OPERAR_GRID o PAUSAR_GRID
    adx_valor: float
    volatilidad_valor: float
    sentiment_promedio: float
    timestamp: str

async def consultar_estado_inicial_cerebro():
    """
    Consulta el estado inicial del Cerebro al arrancar el Grid
    """
    global estado_cerebro
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8004/grid/status/ETH-USDT")
            
            if response.status_code == 200:
                data = response.json()
                estado_cerebro.update({
                    "decision": data.get("decision", "PAUSAR_GRID"),
                    "ultima_actualizacion": data.get("timestamp"),
                    "fuente": data.get("fuente", "cerebro_consulta_inicial")
                })
                
                logger.info(f"🧠 Estado inicial del Cerebro: {estado_cerebro['decision']}")
                logger.info(f"📊 ADX: {data.get('adx_valor')}, Volatilidad: {data.get('volatilidad_valor')}")
                
                return True
            else:
                logger.warning(f"⚠️ Error consultando Cerebro: {response.status_code}")
                
    except Exception as e:
        logger.warning(f"⚠️ No se pudo conectar con el Cerebro: {e}")
        logger.info("🔄 Grid continuará con decisión por defecto: PAUSAR_GRID")
    
    return False

def obtener_configuracion_trading():
    """
    Retorna la configuración de trading según el modo activo
    """
    from shared.config.settings import settings
    
    if MODO_PRODUCTIVO:
        return {
            "api_key": settings.BINANCE_API_KEY,
            "api_secret": settings.BINANCE_API_SECRET,
            "modo": "PRODUCTIVO",
            "descripcion": "Trading real en Binance"
        }
    else:
        return {
            "api_key": settings.PAPER_TRADING_API_KEY,
            "api_secret": settings.PAPER_TRADING_SECRET_KEY,
            "modo": "SANDBOX",
            "descripcion": "Paper trading para pruebas"
        }

def alternar_modo_trading():
    """
    Alterna entre modo productivo y sandbox
    Retorna el nuevo modo y configuración
    """
    global MODO_PRODUCTIVO
    MODO_PRODUCTIVO = not MODO_PRODUCTIVO
    
    config = obtener_configuracion_trading()
    logger.info(f"🔄 Modo cambiado a: {config['modo']}")
    
    return config

def start_telegram_bot():
    """
    Inicia el bot de Telegram para control remoto del grid bot
    """
    global telegram_bot, telegram_interface, telegram_thread
    
    try:
        from shared.config.settings import settings
        
        # Verificar si hay token configurado
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("⚠️ Token de Telegram no configurado - Bot de Telegram deshabilitado")
            return None
        
        # Crear instancia del bot
        telegram_bot = TelegramBot()
        
        # Crear interfaz específica del grid
        telegram_interface = GridTelegramInterface(telegram_bot)
        
        # Iniciar polling en hilo separado
        telegram_thread = telegram_bot.start_background_polling(interval=2)
        
        logger.info("🤖 Bot de Telegram iniciado correctamente")
        return telegram_bot
        
    except Exception as e:
        logger.error(f"❌ Error iniciando bot de Telegram: {e}")
        return None

def stop_telegram_bot():
    """
    Detiene el bot de Telegram
    """
    global telegram_bot, telegram_interface, telegram_thread
    
    try:
        if telegram_thread and telegram_thread.is_alive():
            logger.info("🛑 Deteniendo bot de Telegram...")
            # El hilo del bot se detendrá automáticamente al salir del programa
            telegram_thread = None
        
        telegram_bot = None
        telegram_interface = None
        
        logger.info("✅ Bot de Telegram detenido")
        
    except Exception as e:
        logger.error(f"❌ Error deteniendo bot de Telegram: {e}")

def start_grid_service():
    """
    Inicia el servicio completo de grid trading con todos sus schedulers.
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
        
        # Configurar e iniciar scheduler en modo standby (incluye limpieza automática de órdenes huérfanas)
        from services.grid.schedulers.grid_scheduler import start_grid_bot_scheduler
        start_grid_bot_scheduler()
        scheduler = get_grid_scheduler()
        
        # Iniciar bot de Telegram
        telegram_bot_instance = start_telegram_bot()
        
        # Consultar estado inicial del Cerebro de forma asíncrona
        logger.info("🧠 Consultando estado inicial del Cerebro...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(consultar_estado_inicial_cerebro())
        loop.close()
        
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
    Detiene el servicio de grid trading y todos sus schedulers.
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

# Gestor de Ciclo de Vida para FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando FastAPI del Grid Worker...")
    try:
        start_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Worker: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando FastAPI del Grid Worker...")
    try:
        stop_grid_service()
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Worker: {e}")

# Aplicación FastAPI minimal para health checks
app = FastAPI(
    title="Oráculo Bot - Grid Worker",
    version="0.1.0",
    description="Worker de grid trading automatizado para Binance con integración Cerebro v3.0",
    lifespan=lifespan
)

# Endpoints mínimos para health checks
@app.get("/", tags=["Worker"])
def read_root():
    """Endpoint básico para verificar que el Grid Worker está vivo."""
    return {
        "worker": "grid",
        "status": "alive",
        "description": "Worker de trading - Grid trading automatizado en Binance"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check específico para el grid worker."""
    try:
        scheduler = get_grid_scheduler()
        is_running = scheduler.running if scheduler else False
        
        jobs_count = len(scheduler.get_jobs()) if scheduler and is_running else 0
        
        # Verificar estado del bot de Telegram
        telegram_running = telegram_thread is not None and telegram_thread.is_alive()
        
        features = [
            "🤖 Grid trading strategy",
            "💹 Binance automated trading",
            "🔄 Health monitoring every 5 minutes"
        ]
        
        if telegram_running:
            features.append("🤖 Telegram bot active")
        
        return {
            "worker": "grid",
            "status": "healthy" if is_running else "stopped",
            "scheduler_running": is_running,
            "telegram_bot_running": telegram_running,
            "active_jobs": jobs_count,
            "features": features
        }
    except Exception as e:
        return {
            "worker": "grid",
            "status": "error",
            "error": str(e)
        }

# ============================================================================
# ENDPOINTS PARA INTEGRACIÓN CON CEREBRO
# ============================================================================

@app.post("/cerebro/decision", tags=["Cerebro"])
async def recibir_decision_cerebro(decision: DecisionCerebro):
    """
    Endpoint para recibir decisiones automáticas del Cerebro
    """
    global estado_cerebro
    
    try:
        # Actualizar estado global
        estado_cerebro.update({
            "decision": decision.decision,
            "ultima_actualizacion": decision.timestamp,
            "fuente": "cerebro_notificacion_automatica"
        })
        
        logger.info(f"🧠 Nueva decisión del Cerebro: {decision.decision}")
        logger.info(f"📊 Par: {decision.par} | ADX: {decision.adx_valor} | Volatilidad: {decision.volatilidad_valor}")
        
        # Aquí puedes agregar lógica para actuar sobre la decisión
        # Por ejemplo, pausar/reanudar el grid trading
        
        return {
            "status": "success",
            "message": f"Decisión {decision.decision} recibida y procesada",
            "timestamp": decision.timestamp
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando decisión del Cerebro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cerebro/estado", tags=["Cerebro"])
def obtener_estado_cerebro():
    """
    Obtiene el estado actual de la decisión del Cerebro
    """
    config = obtener_configuracion_trading()
    
    return {
        "estado_cerebro": estado_cerebro,
        "modo_trading": config["modo"],
        "timestamp": estado_cerebro.get("ultima_actualizacion"),
        "status": "active"
    }

@app.post("/modo/alternar", tags=["Configuración"])
def alternar_modo_trading_endpoint():
    """
    Alterna entre modo productivo y sandbox
    """
    try:
        config = alternar_modo_trading()
        
        return {
            "status": "success",
            "nuevo_modo": config["modo"],
            "descripcion": config["descripcion"],
            "message": f"Modo cambiado a {config['modo']}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error alternando modo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Punto de entrada directo (sin FastAPI)
    try:
        scheduler = start_grid_service()
        
        # Mantener el servicio corriendo
        import time
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