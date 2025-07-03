"""
Scheduler simplificado para Grid Trading.
Ejecuta monitoreo cada hora sin dependencia del Cerebro.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.application.monitor_grid_orders_use_case import MonitorGridOrdersUseCase
from app.infrastructure.database_repository import DatabaseGridRepository
from app.infrastructure.exchange_service import BinanceExchangeService
from app.infrastructure.notification_service import TelegramGridNotificationService
from app.infrastructure.grid_calculator import GridTradingCalculator
from app.config import MONITORING_INTERVAL_HOURS
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GridScheduler:
    """
    Scheduler simplificado que ejecuta monitoreo de grid cada hora.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.scheduler = BackgroundScheduler(daemon=True)
        
        # Inicializar dependencias
        self._initialize_services()
        
        # Configurar trabajos
        self._setup_jobs()
        
        logger.info("✅ GridScheduler inicializado.")

    def _initialize_services(self):
        """Inicializa todos los servicios necesarios."""
        try:
            self.grid_repository = DatabaseGridRepository(self.db_session)
            self.exchange_service = BinanceExchangeService()
            self.notification_service = TelegramGridNotificationService()
            self.grid_calculator = GridTradingCalculator()
            
            self.monitor_use_case = MonitorGridOrdersUseCase(
                grid_repository=self.grid_repository,
                exchange_service=self.exchange_service,
                notification_service=self.notification_service,
                grid_calculator=self.grid_calculator
            )
            
            logger.info("✅ Servicios de Grid inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando servicios: {e}")
            raise

    def _setup_jobs(self):
        """Configura los trabajos del scheduler."""
        try:
            # Trabajo principal: Monitoreo cada hora
            self.scheduler.add_job(
                func=self._run_grid_monitoring,
                trigger=IntervalTrigger(hours=MONITORING_INTERVAL_HOURS),
                id='grid_monitoring',
                name='Grid Trading Monitoring',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300  # 5 minutos de gracia
            )
            
            logger.info(f"✅ Trabajo de monitoreo configurado cada {MONITORING_INTERVAL_HOURS} hora(s)")
            
        except Exception as e:
            logger.error(f"❌ Error configurando trabajos del scheduler: {e}")
            raise

    def _run_grid_monitoring(self):
        """Ejecuta el monitoreo de grid trading."""
        try:
            logger.info("🔄 ========== INICIANDO CICLO DE MONITOREO GRID ==========")
            
            # Ejecutar caso de uso de monitoreo
            result = self.monitor_use_case.execute()
            
            if result.get('success', False):
                monitored_bots = result.get('monitored_bots', 0)
                total_actions = result.get('total_actions', 0)
                
                logger.info(f"✅ Monitoreo completado: {monitored_bots} bots, {total_actions} acciones")
                
                # Enviar resumen si hubo actividad significativa
                if total_actions > 0:
                    self.notification_service.send_grid_summary(
                        active_bots=monitored_bots,
                        total_trades=total_actions,  # Simplificado por ahora
                        total_profit=0.0  # Se calculará en futuras versiones
                    )
            else:
                error = result.get('error', 'Error desconocido')
                logger.error(f"❌ Error en monitoreo: {error}")
                self.notification_service.send_error_notification("Grid Trading Monitor", error)
            
            logger.info("✅ ========== CICLO DE MONITOREO GRID COMPLETADO ==========")
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de monitoreo: {e}")
            self.notification_service.send_error_notification("Grid Trading Monitor", str(e))

    def start(self):
        """Inicia el scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("✅ Grid Scheduler iniciado")
                logger.info(f"🔄 Monitoreo cada {MONITORING_INTERVAL_HOURS} hora(s)")
            else:
                logger.warning("⚠️ Grid Scheduler ya está ejecutándose")
                
        except Exception as e:
            logger.error(f"❌ Error iniciando Grid Scheduler: {e}")
            raise

    def stop(self):
        """Detiene el scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Grid Scheduler detenido")
            else:
                logger.info("ℹ️ Grid Scheduler no estaba ejecutándose")
                
        except Exception as e:
            logger.error(f"❌ Error deteniendo Grid Scheduler: {e}")

    def is_running(self) -> bool:
        """Verifica si el scheduler está ejecutándose."""
        return self.scheduler.running if self.scheduler else False

    def get_status(self) -> dict:
        """Obtiene el estado actual del scheduler."""
        try:
            if not self.scheduler:
                return {"status": "not_initialized"}
            
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None
                })
            
            return {
                "status": "running" if self.scheduler.running else "stopped",
                "jobs": jobs,
                "monitoring_interval_hours": MONITORING_INTERVAL_HOURS
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del scheduler: {e}")
            return {"status": "error", "error": str(e)}

    def trigger_manual_monitoring(self):
        """Ejecuta manualmente el monitoreo (útil para comandos de Telegram)."""
        try:
            logger.info("🔧 Ejecutando monitoreo manual...")
            self._run_grid_monitoring()
            return {"success": True, "message": "Monitoreo manual ejecutado"}
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo manual: {e}")
            return {"success": False, "error": str(e)} 