from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.logging_config import get_logger
from app.services.grid_trading_service import run_grid_trading_bot

logger = get_logger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler()

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
    Función que ejecuta el grid bot
    """
    try:
        logger.info("🤖 Iniciando ejecución del Grid Bot...")
        config = get_grid_bot_config()
        
        # Ejecutar el grid trading bot
        run_grid_trading_bot(config)
        
    except Exception as e:
        logger.error(f"❌ Error al ejecutar Grid Bot: {e}")

def start_grid_bot_scheduler():
    """
    Inicia el scheduler del grid bot
    """
    try:
        # El grid bot normalmente se ejecuta continuamente, no en intervalos
        # Pero podemos usar el scheduler para reiniciarlo en caso de fallos
        scheduler.add_job(
            func=run_grid_bot,
            trigger=IntervalTrigger(hours=24),  # Se reinicia cada 24 horas
            id='grid_bot_job',
            name='Grid Trading Bot',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Grid Bot Scheduler iniciado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Grid Bot Scheduler: {e}")
        raise

def stop_grid_bot_scheduler():
    """
    Detiene el scheduler del grid bot
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Grid Bot Scheduler detenido correctamente")
    except Exception as e:
        logger.error(f"❌ Error al detener Grid Bot Scheduler: {e}") 