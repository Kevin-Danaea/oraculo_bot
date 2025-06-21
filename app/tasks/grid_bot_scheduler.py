from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading
import time
from app.core.logging_config import get_logger
from app.services.grid_trading_service import run_grid_trading_bot

logger = get_logger(__name__)

# Instancia global del scheduler y estado del bot
scheduler = BackgroundScheduler()
grid_bot_thread = None
grid_bot_running = False

def get_grid_bot_config():
    """
    Configuración del grid bot
    Puedes modificar esta función para cargar la configuración desde base de datos
    """
    return {
        'pair': 'ETH/USDT',
        'total_capital': 56.88,
        'grid_levels': 4,
        'price_range_percent': 20.0,
    }

def run_grid_bot():
    """
    Función wrapper que ejecuta el grid bot en un hilo separado
    """
    global grid_bot_running, grid_bot_thread
    
    try:
        if grid_bot_running:
            logger.warning("⚠️ Grid Bot ya está ejecutándose, omitiendo nueva ejecución")
            return
            
        logger.info("🤖 Iniciando ejecución del Grid Bot...")
        grid_bot_running = True
        
        config = get_grid_bot_config()
        
        # Ejecutar el grid trading bot (función que corre indefinidamente)
        run_grid_trading_bot(config)
        
    except Exception as e:
        logger.error(f"❌ Error al ejecutar Grid Bot: {e}")
    finally:
        grid_bot_running = False

def run_grid_bot_thread():
    """
    Ejecuta el grid bot en un hilo separado para no bloquear el scheduler
    """
    global grid_bot_thread, grid_bot_running
    
    try:
        if grid_bot_thread and grid_bot_thread.is_alive():
            logger.warning("⚠️ Hilo del Grid Bot ya está ejecutándose")
            return
            
        # Crear y iniciar el hilo del grid bot
        grid_bot_thread = threading.Thread(target=run_grid_bot, daemon=True, name="GridBotThread")
        grid_bot_thread.start()
        
        logger.info("✅ Grid Bot iniciado en hilo separado")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando hilo del Grid Bot: {e}")

def check_grid_bot_health():
    """
    Función que verifica si el grid bot sigue ejecutándose y lo reinicia si es necesario
    """
    global grid_bot_thread, grid_bot_running
    
    try:
        # Verificar estado del hilo
        if not grid_bot_thread or not grid_bot_thread.is_alive():
            if grid_bot_running:
                # El hilo murió pero se supone que debería estar corriendo
                logger.warning("⚠️ Grid Bot se detuvo inesperadamente, reiniciando...")
                grid_bot_running = False
                run_grid_bot_thread()
            elif not grid_bot_running:
                # Primera ejecución o reinicio normal
                logger.info("🔄 Iniciando Grid Bot...")
                run_grid_bot_thread()
        else:
            logger.debug("✅ Grid Bot ejecutándose correctamente")
            
    except Exception as e:
        logger.error(f"❌ Error verificando salud del Grid Bot: {e}")

def start_grid_bot_scheduler():
    """
    Inicia el scheduler del grid bot con monitoreo de salud
    """
    try:
        # Programar verificación de salud cada 5 minutos
        scheduler.add_job(
            func=check_grid_bot_health,
            trigger=IntervalTrigger(minutes=5),
            id='grid_bot_health_check',
            name='Grid Bot Health Check',
            replace_existing=True,
            max_instances=1,  # Solo una instancia a la vez
            misfire_grace_time=60  # 1 minuto de gracia para ejecuciones perdidas
        )
        
        # Iniciar el scheduler
        scheduler.start()
        logger.info("✅ Grid Bot Scheduler iniciado correctamente")
        logger.info("🔄 Verificación de salud programada cada 5 minutos")
        
        # Iniciar inmediatamente el grid bot
        time.sleep(2)  # Esperar un poco para que el scheduler se stabilice
        check_grid_bot_health()
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Bot Scheduler: {e}")
        raise

def stop_grid_bot_scheduler():
    """
    Detiene el scheduler y el grid bot
    """
    global grid_bot_running, grid_bot_thread
    
    try:
        # Marcar que se debe detener el bot
        if grid_bot_running:
            logger.info("🛑 Señalando detención del Grid Bot...")
            grid_bot_running = False
        
        # Detener el scheduler
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Grid Bot Scheduler detenido correctamente")
            
        # Esperar a que termine el hilo del bot (máximo 30 segundos)
        if grid_bot_thread and grid_bot_thread.is_alive():
            logger.info("⏳ Esperando que termine el Grid Bot...")
            grid_bot_thread.join(timeout=30)
            if grid_bot_thread.is_alive():
                logger.warning("⚠️ Grid Bot no terminó en el tiempo esperado")
            else:
                logger.info("✅ Grid Bot terminado correctamente")
                
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Bot Scheduler: {e}") 