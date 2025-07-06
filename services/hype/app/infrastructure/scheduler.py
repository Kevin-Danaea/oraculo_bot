"""
Scheduler para ejecutar los casos de uso del Hype Radar periódicamente.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from typing import List
import pytz

# Importaciones de la aplicación
from app.application.scan_and_detect_hype_use_case import ScanAndDetectHypeUseCase
from app.application.send_daily_summary_use_case import SendDailySummaryUseCase
from app.infrastructure.reddit_adapter import RedditHypeCollector
from app.infrastructure.database_repository import DatabaseHypeRepository
from app.infrastructure.notification_adapter import TelegramNotificationService
from app.infrastructure.hype_analyzer_adapter import HypeAnalyzerAdapter

# Importaciones compartidas
from shared.database.session import get_db
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class HypeScheduler:
    """
    Gestiona la ejecución periódica de los trabajos de escaneo de hype.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.scheduler = BackgroundScheduler(daemon=True)
        
        # Inicialización centralizada de dependencias para los casos de uso
        hype_collector = RedditHypeCollector()
        hype_repository = DatabaseHypeRepository(self.db_session)
        notification_service = TelegramNotificationService()
        hype_analyzer = HypeAnalyzerAdapter()
        
        self.scan_use_case = ScanAndDetectHypeUseCase(
            hype_collector=hype_collector,
            hype_analyzer=hype_analyzer,
            hype_repository=hype_repository,
            notification_service=notification_service
        )
        
        self.daily_summary_use_case = SendDailySummaryUseCase(
            hype_repository=hype_repository,
            notification_service=notification_service
        )

    def _run_alerting_job(self, subreddits_to_scan: List[str]):
        """
        Trabajo de ALERTA: Escanea, analiza y envía alertas, pero no guarda el escaneo completo.
        Se ejecuta con alta frecuencia.
        """
        logger.info("⏰ Tarea de ALERTA: Ejecutando escaneo de Hype Radar...")
        self.scan_use_case.execute(subreddits_to_scan=subreddits_to_scan, save_scan_result=False)
        logger.info("✅ Tarea de ALERTA: Escaneo finalizado.")

    def _run_saving_job(self, subreddits_to_scan: List[str]):
        """
        Trabajo de GUARDADO: Escanea, analiza, y guarda el resultado completo del escaneo.
        Se ejecuta con baja frecuencia para mantener un historial.
        """
        logger.info("💾 Tarea de GUARDADO: Ejecutando escaneo completo y guardado...")
        self.scan_use_case.execute(subreddits_to_scan=subreddits_to_scan, save_scan_result=True)
        logger.info("✅ Tarea de GUARDADO: Escaneo y guardado finalizados.")

    def _run_daily_summary_job(self):
        """
        Trabajo de RESUMEN DIARIO: Genera y envía un resumen de las tendencias del día.
        Se ejecuta una vez al día a las 11:00 AM.
        """
        logger.info("📊 Tarea de RESUMEN DIARIO: Generando resumen...")
        result = self.daily_summary_use_case.execute(hours=24)
        
        if result.get('success', False):
            events_count = result.get('events_count', 0)
            logger.info(f"✅ Resumen diario enviado exitosamente ({events_count} eventos procesados)")
        else:
            error = result.get('error', 'Error desconocido')
            logger.error(f"❌ Error en resumen diario: {error}")
        
        logger.info("✅ Tarea de RESUMEN DIARIO: Finalizada.")

    def start(self, subreddits_to_scan: List[str], alert_interval_minutes: int = 5, save_interval_hours: int = 24):
        """
        Inicia el scheduler con los dos trabajos.
        """
        if not self.scheduler.running:
            # Tarea de ALERTA (alta frecuencia)
            self.scheduler.add_job(
                self._run_alerting_job,
                trigger=IntervalTrigger(minutes=alert_interval_minutes),
                args=[subreddits_to_scan],
                id='hype_alerting_job',
                name='Hype Alerting Scan (No DB Save)',
                replace_existing=True
            )
            
            # Tarea de GUARDADO (baja frecuencia)
            self.scheduler.add_job(
                self._run_saving_job,
                trigger=IntervalTrigger(hours=save_interval_hours),
                args=[subreddits_to_scan],
                id='hype_saving_job',
                name='Hype Saving Scan (With DB Save)',
                replace_existing=True
            )
            
            # Tarea de RESUMEN DIARIO (11:00 AM hora de México)
            mexico_tz = pytz.timezone('America/Mexico_City')
            self.scheduler.add_job(
                self._run_daily_summary_job,
                trigger=CronTrigger(hour=11, minute=0, timezone=mexico_tz),
                id='hype_daily_summary',
                name='Daily Hype Summary (11:00 AM Mexico City Time)',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info(f"📅 Scheduler de Hype iniciado:")
            logger.info(f"  -> 🎯 Tarea de Alerta cada {alert_interval_minutes} minutos.")
            logger.info(f"  -> 💾 Tarea de Guardado cada {save_interval_hours} horas.")
            logger.info(f"  -> 📊 Resumen Diario a las 11:00 AM (hora de México)")
        else:
            logger.warning("⚠️ El scheduler de Hype ya está en ejecución.")

    def stop(self):
        """
        Detiene el scheduler si está en ejecución.
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler de Hype detenido.")
        else:
            logger.info("ℹ️ El scheduler de Hype no estaba en ejecución.") 