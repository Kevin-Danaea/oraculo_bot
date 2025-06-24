"""
Scheduler del Hype Radar.
Maneja la ejecución periódica de escaneos de tendencias en subreddits de alto riesgo.
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
        from services.hype.core.hype_analytics import get_hype_summary, hype_analyzer
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
            
            # Reiniciar contadores para el nuevo día
            hype_analyzer.reset_alert_counters()
        else:
            logger.info("📊 No hay datos suficientes para resumen diario")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job de resumen diario: {e}")
    
    logger.info("📊 Job de resumen diario finalizado.")

def run_hype_radar_job():
    """
    Tarea que ejecuta el escaneo del hype radar.
    Se ejecuta cada hora para detectar tendencias emergentes.
    """
    logger.info("🎯 Iniciando job de escaneo del Hype Radar...")
    db = SessionLocal()
    try:
        # Ejecutar el escaneo completo
        result = hype_radar_service.execute_hype_radar_scan(db)
        
        if result.get('success', False):
            posts_analyzed = result.get('total_posts_analyzed', 0)
            posts_with_mentions = result.get('total_posts_with_mentions', 0)
            unique_tickers = result.get('unique_tickers_mentioned', 0)
            alerts_sent = result.get('alerts_sent', 0)
            
            logger.info(f"✅ Escaneo completado: {posts_analyzed} posts analizados, {posts_with_mentions} con menciones, {unique_tickers} tickers únicos")
            
            if alerts_sent > 0:
                logger.info(f"🚨 {alerts_sent} alertas de hype enviadas")
            
            # Mostrar top tickers si los hay
            top_tickers = result.get('top_trending_tickers', {})
            if top_tickers:
                logger.info("🔥 Tendencias detectadas:")
                for ticker, count in list(top_tickers.items())[:5]:
                    logger.info(f"   📈 {ticker}: {count} menciones")
        else:
            error = result.get('error', 'Error desconocido')
            logger.error(f"❌ Error en escaneo del hype radar: {error}")
            
    except Exception as e:
        logger.error(f"💥 Error inesperado en job del hype radar: {e}")
    finally:
        db.close()
    logger.info("🎯 Job de escaneo del Hype Radar finalizado.")

def setup_hype_scheduler():
    """
    Configura y retorna el scheduler del hype radar con todas las tareas programadas.
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # Tarea principal: Escanear hype cada 15 minutos
        _scheduler.add_job(
            run_hype_radar_job, 
            'interval', 
            minutes=15, 
            id='hype_radar_scanner',
            name='Hype Radar Scanner'
        )
        
        # Tarea de resumen diario: Enviar a las 23:00 hora de México Centro (UTC-6)
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
        
        logger.info("✅ Hype Radar scheduler configurado")
        logger.info("🎯 Escaneo de tendencias programado cada 15 minutos")
        logger.info("📊 Resumen diario programado a las 23:00 hora de México Centro (UTC-6)")
    
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

 