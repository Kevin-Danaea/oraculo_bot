from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading
import time
from datetime import datetime
from shared.services.logging_config import get_logger
from services.grid.core.trading_engine import run_grid_trading_bot

logger = get_logger(__name__)

# Instancia global del scheduler y estado del bot
scheduler = BackgroundScheduler()
grid_bot_thread = None
grid_bot_running = False

def get_grid_bot_config():
    """
    Configuración del grid bot - Ahora usa configuración dinámica según el modo
    """
    # Importar función de configuración dinámica
    try:
        from services.grid.interfaces.telegram_interface import get_dynamic_grid_config
        config = get_dynamic_grid_config()
        logger.info(f"✅ Configuración obtenida: {config['modo']} - {config['pair']} - ${config['total_capital']} USDT")
        return config
    except ImportError as e:
        logger.warning(f"⚠️ No se pudo importar configuración dinámica: {e}")
        # Fallback a configuración por defecto según el modo
        from services.grid.main import MODO_PRODUCTIVO
        
        if not MODO_PRODUCTIVO:
            # Configuración fija para sandbox
            logger.info("🟡 Usando configuración fija para SANDBOX (fallback)")
            return {
                'pair': 'ETH/USDT',
                'total_capital': 1000.0,  # Capital fijo para sandbox
                'grid_levels': 30,  # Validado en backtesting
                'price_range_percent': 10.0,  # Validado en backtesting
                'modo': 'SANDBOX'
            }
        else:
            # Configuración mínima para productivo
            logger.info("🟢 Usando configuración mínima para PRODUCTIVO (fallback)")
            return {
                'pair': 'ETH/USDT',
                'total_capital': 750.0,  # Capital mínimo para productivo
                'grid_levels': 30,  # Validado en backtesting
                'price_range_percent': 10.0,  # Validado en backtesting
                'modo': 'PRODUCTIVO'
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
    Función que verifica si el grid bot sigue ejecutándose.
    MODIFICADO V2: Solo reinicia si estaba corriendo previamente, NO inicia automáticamente.
    """
    global grid_bot_thread, grid_bot_running
    
    try:
        # Verificar estado del hilo
        if not grid_bot_thread or not grid_bot_thread.is_alive():
            if grid_bot_running:
                # El hilo murió pero se supone que debería estar corriendo - REINICIAR
                logger.warning("⚠️ Grid Bot se detuvo inesperadamente, reiniciando...")
                grid_bot_running = False
                run_grid_bot_thread()
            else:
                # Bot no está corriendo intencionalmente - MODO STANDBY
                logger.debug("⏸️ Grid Bot en modo standby (esperando comando manual)")
        else:
            logger.info("✅ Grid Bot ejecutándose correctamente")
            
    except Exception as e:
        logger.error(f"❌ Error verificando salud del Grid Bot: {e}")

def check_cerebro_status():
    """
    Verifica el estado del cerebro y actúa automáticamente según la decisión.
    Esta función se ejecuta periódicamente para asegurar sincronización.
    """
    try:
        from services.grid.main import estado_cerebro
        
        decision_actual = estado_cerebro.get('decision', 'No disponible')
        fuente = estado_cerebro.get('fuente', 'No disponible')
        
        # Solo actuar si la decisión viene del cerebro (no de consulta manual)
        if fuente == 'cerebro_notificacion_automatica':
            bot_status = get_grid_bot_status()
            
            if decision_actual == "OPERAR_GRID" and not bot_status['bot_running']:
                logger.info("🧠 Monitoreo: Cerebro autoriza trading - Iniciando Grid Bot...")
                success, message = start_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot iniciado por monitoreo del cerebro")
                else:
                    logger.error(f"❌ Error iniciando Grid Bot por monitoreo: {message}")
                    
            elif decision_actual == "PAUSAR_GRID" and bot_status['bot_running']:
                logger.info("🧠 Monitoreo: Cerebro recomienda pausar - Deteniendo Grid Bot...")
                success, message = stop_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot detenido por monitoreo del cerebro")
                else:
                    logger.error(f"❌ Error deteniendo Grid Bot por monitoreo: {message}")
        
    except Exception as e:
        logger.error(f"❌ Error en monitoreo del cerebro: {e}")

def setup_grid_scheduler():
    """
    Configura el scheduler del grid bot y retorna la instancia
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
        
        # Programar monitoreo del cerebro cada 10 minutos
        scheduler.add_job(
            func=check_cerebro_status,
            trigger=IntervalTrigger(minutes=10),
            id='cerebro_status_check',
            name='Cerebro Status Check',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60
        )
        
        logger.info("✅ Grid Bot Scheduler configurado correctamente")
        logger.info("🔄 Verificación de salud programada cada 5 minutos")
        logger.info("🧠 Monitoreo del cerebro programado cada 10 minutos")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Error al configurar Grid Bot Scheduler: {e}")
        raise

def start_grid_bot_scheduler():
    """
    Inicia el scheduler del grid bot en MODO STANDBY.
    V3: MODO AUTÓNOMO - Responde automáticamente a decisiones del Cerebro
    """
    try:
        # Configurar scheduler
        setup_grid_scheduler()
        
        # Iniciar el scheduler
        scheduler.start()
        logger.info("✅ Grid Bot Scheduler iniciado correctamente")
        
        # V3: MODO AUTÓNOMO - Responde a decisiones del Cerebro
        logger.info("🧠 Grid Bot en MODO AUTÓNOMO - Responde a decisiones del Cerebro")
        logger.info("🔄 Monitoreo automático cada 10 minutos")
        logger.info("📱 Comandos manuales disponibles: /start_bot, /stop_bot")
        
        # Inicializar limpieza de órdenes huérfanas
        try:
            from ..core.startup_manager import initialize_standby_mode
            initialize_standby_mode()
        except ImportError:
            logger.warning("⚠️ No se pudo importar startup_manager, saltando limpieza automática")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Bot Scheduler: {e}")
        raise

def get_grid_scheduler():
    """
    Retorna la instancia del scheduler para uso externo
    """
    return scheduler

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

def start_grid_bot_manual():
    """
    Inicia el grid bot manualmente (comando desde Telegram)
    V2: Función específica para inicio manual del trading
    """
    global grid_bot_running, grid_bot_thread
    
    try:
        if grid_bot_running:
            logger.warning("⚠️ Grid Bot ya está ejecutándose")
            return False, "El bot ya está ejecutándose"
        
        if grid_bot_thread and grid_bot_thread.is_alive():
            logger.warning("⚠️ Hilo del Grid Bot aún está activo")
            return False, "Hay un proceso del bot aún activo"
        
        # Iniciar el bot
        logger.info("🚀 Iniciando Grid Bot por comando manual...")
        run_grid_bot_thread()
        
        # Esperar un momento para verificar que inició correctamente
        time.sleep(3)
        
        if grid_bot_running and grid_bot_thread and grid_bot_thread.is_alive():
            logger.info("✅ Grid Bot iniciado exitosamente por comando manual")
            return True, "Grid Bot iniciado exitosamente"
        else:
            logger.error("❌ Error al iniciar Grid Bot manualmente")
            return False, "Error al iniciar el bot"
            
    except Exception as e:
        logger.error(f"❌ Error en inicio manual del Grid Bot: {e}")
        return False, f"Error: {str(e)}"

def stop_grid_bot_manual():
    """
    Detiene el grid bot manualmente (comando desde Telegram)
    V2: Función específica para detención manual del trading
    """
    global grid_bot_running, grid_bot_thread
    
    try:
        if not grid_bot_running:
            logger.warning("⚠️ Grid Bot no está ejecutándose")
            return False, "El bot no está ejecutándose"
        
        # Señalar detención
        logger.info("🛑 Deteniendo Grid Bot por comando manual...")
        grid_bot_running = False
        
        # Esperar a que termine el hilo (máximo 30 segundos)
        if grid_bot_thread and grid_bot_thread.is_alive():
            logger.info("⏳ Esperando que termine el Grid Bot...")
            grid_bot_thread.join(timeout=30)
            
            if grid_bot_thread.is_alive():
                logger.warning("⚠️ Grid Bot no terminó en el tiempo esperado")
                return False, "El bot no se detuvo completamente"
            else:
                logger.info("✅ Grid Bot detenido exitosamente por comando manual")
                return True, "Grid Bot detenido exitosamente"
        else:
            logger.info("✅ Grid Bot detenido (no había hilo activo)")
            return True, "Grid Bot detenido"
            
    except Exception as e:
        logger.error(f"❌ Error en detención manual del Grid Bot: {e}")
        return False, f"Error: {str(e)}"

def get_grid_bot_status():
    """
    Obtiene el estado actual del grid bot.
    V2: Información completa del estado para comandos de Telegram
    """
    global grid_bot_running, grid_bot_thread
    
    try:
        thread_alive = grid_bot_thread and grid_bot_thread.is_alive()
        scheduler_running = scheduler and scheduler.running
        
        return {
            'bot_running': grid_bot_running,
            'thread_alive': thread_alive,
            'scheduler_active': scheduler_running,
            'standby_mode': not grid_bot_running,
            'ready_to_start': scheduler_running and not grid_bot_running,
            'ready_to_stop': grid_bot_running and thread_alive,
            'timestamp': datetime.now().isoformat() if 'datetime' in globals() else time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado del Grid Bot: {e}")
        return {
            'bot_running': False,
            'thread_alive': False,
            'scheduler_active': False,
            'standby_mode': True,
            'ready_to_start': False,
            'ready_to_stop': False,
            'error': str(e)
        }

# Re-exportar para compatibilidad
__all__ = [
    'setup_grid_scheduler',
    'start_grid_bot_scheduler', 
    'stop_grid_bot_scheduler',
    'get_grid_scheduler',
    'get_grid_bot_config',
    'start_grid_bot_manual',
    'stop_grid_bot_manual', 
    'get_grid_bot_status'
] 