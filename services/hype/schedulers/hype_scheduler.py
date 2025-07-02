"""
Scheduler del Hype Radar.
Maneja la ejecución periódica de escaneos de tendencias y el guardado en BD.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from services.hype.services import hype_radar_service
import pytz

logger = get_logger(__name__)

# Instancia global del scheduler
_scheduler = None

def run_daily_summary_job():
    """
    Tarea que envía un resumen diario de las tendencias detectadas.
    Se ejecuta una vez al día.
    """
    logger.info("📊 Iniciando job de resumen diario del Hype Radar...")
    
    try:
        from services.hype.core.hype_analytics import get_hype_summary
        from services.hype.core.notifications import send_daily_hype_summary
        
        # Obtener resumen del día
        summary = get_hype_summary(24)
        
        if summary:
            top_trending = summary.get('top_5', {})
            total_alerts = summary.get('total_alerts_sent', 0)
            
            # Enviar resumen por Telegram
            success = send_daily_hype_summary(top_trending, total_alerts)
            
            if success:
                logger.info(f"✅ Resumen diario enviado: {total_alerts} alertas, {len(top_trending)} trending")
            else:
                logger.error("❌ Error enviando resumen diario")
            
        else:
            logger.info("📊 No hay datos suficientes para resumen diario")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job de resumen diario: {e}")
    
    logger.info("📊 Job de resumen diario finalizado.")

def run_alerting_only_job():
    """
    Tarea de ALERTA (cada 5 min): Escanea y analiza, pero NO guarda en BD.
    Optimizado para ser ligero y rápido, enfocado en detectar alertas en tiempo real.
    """
    logger.info("🎯 (ALERTA) Iniciando escaneo del Hype Radar...")
    try:
        # Se llama al servicio SIN sesión de BD para evitar la escritura.
        result = hype_radar_service.execute_hype_radar_scan(db=None)
        
        if result.get('success', False):
            alerts_sent = result.get('alerts_sent', 0)
            if alerts_sent > 0:
                logger.info(f"🚨 {alerts_sent} alertas de hype enviadas en este ciclo.")
        else:
            error = result.get('error', 'Error desconocido')
            logger.error(f"❌ Error en escaneo de alerta: {error}")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job de alerta: {e}")
    logger.info("🎯 (ALERTA) Job de escaneo finalizado.")


def run_hype_scan_and_save_job():
    """
    Tarea de GUARDADO (cada hora): Escanea, analiza Y GUARDA en la BD.
    Asegura que tengamos un registro histórico de las tendencias sin saturar la BD.
    """
    logger.info("💾 (GUARDADO) Iniciando escaneo completo y guardado en BD...")
    db = SessionLocal()
    try:
        # Se llama al servicio CON una sesión de BD para activar la escritura.
        result = hype_radar_service.execute_hype_radar_scan(db)
        
        if result.get('success', False):
            posts_analyzed = result.get('total_posts_analyzed', 0)
            unique_tickers = result.get('unique_tickers_mentioned', 0)
            logger.info(f"✅ Escaneo para guardado completado: {posts_analyzed} posts, {unique_tickers} tickers únicos.")
        else:
            error = result.get('error', 'Error desconocido')
            logger.error(f"❌ Error en escaneo para guardado: {error}")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job de guardado: {e}")
    finally:
        db.close()
    logger.info("💾 (GUARDADO) Job de guardado en BD finalizado.")


def setup_hype_scheduler():
    """
    Configura el scheduler con tareas separadas para alertar y para guardar.
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # Tarea 1 (Crítica): Escanear para ALERTAS cada 5 minutos.
        _scheduler.add_job(
            run_alerting_only_job, 
            'interval', 
            minutes=5, 
            id='hype_alert_scanner',
            name='Hype Alert Scanner (No DB)'
        )
        
        # Tarea 2 (Logging): Escanear y GUARDAR en BD cada 24 horas.
        _scheduler.add_job(
            run_hype_scan_and_save_job,
            'interval',
            hours=24,
            id='hype_db_logger',
            name='Hype Scan and Save to DB'
        )
        
        # Tarea 3: Resumen diario (sin cambios).
        mexico_tz = pytz.timezone('America/Mexico_City')
        _scheduler.add_job(
            run_daily_summary_job,
            'cron',
            hour=23,
            minute=0,
            timezone=mexico_tz,
            id='hype_daily_summary',
            name='Daily Hype Summary (Mexico City Time)'
        )
        
        logger.info("✅ Hype Radar scheduler configurado con tareas separadas:")
        logger.info("  -> 🎯 Escaneo de ALERTA cada 5 minutos (sin escritura en BD)")
        logger.info("  -> 💾 Escaneo de GUARDADO cada 24 horas (con escritura en BD)")
        logger.info("  -> 📊 Resumen diario a las 23:00 (hora de México)")
    
    return _scheduler

def get_hype_scheduler():
    """
    Retorna la instancia del scheduler del hype radar.
    """
    return _scheduler

def start_hype_scheduler():
    """
    Inicia el scheduler del hype radar.
    """
    scheduler = setup_hype_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ Hype Radar scheduler iniciado")
    return scheduler

def stop_hype_scheduler():
    """
    Detiene el scheduler del hype radar.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("✅ Hype Radar scheduler detenido")
        _scheduler = None

 