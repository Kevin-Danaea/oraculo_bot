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
import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
import httpx
from pydantic import BaseModel

# Imports para el bot de Telegram
from shared.services.telegram_bot_service import TelegramBot
from shared.services.telegram_service import send_service_startup_notification
from shared.database.session import init_database
from services.grid.schedulers.grid_scheduler import get_grid_scheduler, stop_grid_bot_scheduler
from shared.services.logging_config import setup_logging, get_logger
from services.grid.interfaces.telegram_interface import GridTelegramInterface

logger = get_logger(__name__)

# Variables globales para el bot de Telegram
telegram_bot = None
telegram_interface = None
telegram_thread = None

# Estado del cerebro para integración
estado_cerebro = {
    "decision": "No disponible",
    "ultima_actualizacion": None,
    "fuente": "no_inicializado"
}

# ============================================================================
# INTEGRACIÓN CON CEREBRO V3.0
# ============================================================================

# Variable global para controlar modo productivo/sandbox
MODO_PRODUCTIVO = True  # True = Productivo, False = Sandbox/Paper Trading

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
    Consulta el estado inicial del cerebro para el par configurado.
    
    Returns:
        Dict con la decisión del cerebro
    """
    global estado_cerebro
    
    try:
        # Por ahora, usar ETH/USDT como par por defecto
        # En el futuro, esto se puede mejorar para obtener la configuración del usuario
        par = "ETH/USDT"
        
        # Consultar al cerebro
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8004/grid/status/{par.replace('/', '-')}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                resultado = response.json()
                
                # Actualizar estado global
                estado_cerebro.update({
                    "decision": resultado.get('decision', 'No disponible'),
                    "ultima_actualizacion": resultado.get('timestamp'),
                    "fuente": resultado.get('fuente', 'consulta_manual')
                })
                
                logger.info(f"✅ Estado del cerebro consultado: {par} -> {resultado.get('decision')}")
                return resultado
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"❌ Error consultando cerebro: {e}")
        raise

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

# Endpoints mínimos para health checks
@app.get("/", tags=["Worker"])
def read_root():
    """Endpoint básico para verificar que el Grid Worker está vivo."""
    return {
        "worker": "grid",
        "status": "alive",
        "description": "Worker de trading - Grid trading automatizado en Binance"
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de health check para el Grid Worker.
    """
    try:
        # Verificar que el scheduler esté activo
        scheduler = get_grid_scheduler()
        if scheduler and scheduler.running:
            return {
                "status": "healthy",
                "service": "Grid Trading Service",
                "version": "3.0.0",
                "scheduler": "running",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "service": "Grid Trading Service", 
                "version": "3.0.0",
                "scheduler": "stopped",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "Grid Trading Service",
            "version": "3.0.0", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============================================================================
# ENDPOINTS PARA INTEGRACIÓN CON CEREBRO
# ============================================================================

@app.post("/cerebro/decision", tags=["Cerebro"])
async def recibir_decision_cerebro(decision: DecisionCerebro):
    """
    Endpoint para recibir decisiones automáticas del Cerebro
    IMPLEMENTACIÓN AUTÓNOMA: El Grid responde automáticamente a las decisiones
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
        
        # LÓGICA AUTÓNOMA: Actuar según la decisión del cerebro
        from services.grid.schedulers.grid_scheduler import get_grid_bot_status, start_grid_bot_manual, stop_grid_bot_manual
        
        bot_status = get_grid_bot_status()
        
        if decision.decision == "OPERAR_GRID":
            if not bot_status['bot_running']:
                logger.info("🚀 Cerebro autoriza trading - Iniciando Grid Bot automáticamente...")
                success, message = start_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot iniciado automáticamente por decisión del Cerebro")
                    # Enviar notificación por Telegram
                    try:
                        from shared.services.telegram_service import send_telegram_message
                        send_telegram_message(
                            f"🧠 <b>Grid iniciado automáticamente</b>\n\n"
                            f"✅ El Cerebro autorizó el trading\n"
                            f"📊 Par: {decision.par}\n"
                            f"📈 ADX: {decision.adx_valor:.2f}\n"
                            f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                            f"⏰ {decision.timestamp}"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
                else:
                    logger.error(f"❌ Error iniciando Grid Bot automáticamente: {message}")
            else:
                logger.info("ℹ️ Grid Bot ya está ejecutándose - Cerebro confirma continuar")
                
        elif decision.decision == "PAUSAR_GRID":
            if bot_status['bot_running']:
                logger.info("🛑 Cerebro recomienda pausar - Deteniendo Grid Bot automáticamente...")
                success, message = stop_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot detenido automáticamente por decisión del Cerebro")
                    # Enviar notificación por Telegram
                    try:
                        from shared.services.telegram_service import send_telegram_message
                        send_telegram_message(
                            f"🧠 <b>Grid pausado automáticamente</b>\n\n"
                            f"⚠️ El Cerebro recomendó pausar el trading\n"
                            f"📊 Par: {decision.par}\n"
                            f"📈 ADX: {decision.adx_valor:.2f}\n"
                            f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                            f"⏰ {decision.timestamp}\n\n"
                            f"🔄 El Grid se reactivará automáticamente cuando el Cerebro autorice"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
                else:
                    logger.error(f"❌ Error deteniendo Grid Bot automáticamente: {message}")
            else:
                logger.info("ℹ️ Grid Bot ya está pausado - Cerebro confirma mantener pausado")
        
        return {
            "status": "success",
            "message": f"Decisión {decision.decision} procesada y ejecutada automáticamente",
            "action_taken": "start" if decision.decision == "OPERAR_GRID" and not bot_status['bot_running'] else 
                           "stop" if decision.decision == "PAUSAR_GRID" and bot_status['bot_running'] else "none",
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