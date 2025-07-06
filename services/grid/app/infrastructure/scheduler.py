"""
Scheduler híbrido para Grid Trading:
- Monitor en tiempo real (cada 10 segundos): Detecta fills y crea órdenes complementarias
- Gestión horaria: Transiciones de estado basadas en decisiones del Cerebro
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.application.manage_grid_transitions_use_case import ManageGridTransitionsUseCase
from app.application.realtime_grid_monitor_use_case import RealTimeGridMonitorUseCase
from app.application.trading_stats_use_case import TradingStatsUseCase
from app.infrastructure.database_repository import DatabaseGridRepository
from app.infrastructure.exchange_service import BinanceExchangeService
from app.infrastructure.notification_service import TelegramGridNotificationService
from app.infrastructure.grid_calculator import GridTradingCalculator
from app.config import MONITORING_INTERVAL_HOURS, REALTIME_MONITOR_INTERVAL_SECONDS
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GridScheduler:
    """
    Scheduler híbrido que combina:
    
    ⚡ TIEMPO REAL (cada 10 segundos):
    - RealTimeGridMonitorUseCase: Detecta fills inmediatamente
    - Crea órdenes complementarias al instante
    - Optimizado para aprovechar movimientos de corto plazo
    
    ⏰ GESTIÓN HORARIA:
    - ManageGridTransitionsUseCase: Pausar/activar según Cerebro
    - Sincronización de configuraciones activas
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.scheduler = BackgroundScheduler(daemon=True)
        
        # Inicializar dependencias
        self._initialize_services()
        
        # Configurar trabajos
        self._setup_jobs()
        
        logger.info("✅ GridScheduler híbrido inicializado (Tiempo Real + Hourly).")

    def _initialize_services(self):
        """Inicializa todos los servicios necesarios."""
        try:
            self.grid_repository = DatabaseGridRepository(self.db_session)
            self.exchange_service = BinanceExchangeService()
            self.notification_service = TelegramGridNotificationService()
            self.grid_calculator = GridTradingCalculator()
            
            # Casos de uso especializados
            self.transition_use_case = ManageGridTransitionsUseCase(
                grid_repository=self.grid_repository,
                exchange_service=self.exchange_service,
                notification_service=self.notification_service,
                grid_calculator=self.grid_calculator
            )
            
            # NUEVO: Monitor en tiempo real
            self.realtime_monitor_use_case = RealTimeGridMonitorUseCase(
                grid_repository=self.grid_repository,
                exchange_service=self.exchange_service,
                notification_service=self.notification_service,
                grid_calculator=self.grid_calculator
            )
            
            # NUEVO: Estadísticas de trading para notificaciones
            self.trading_stats_use_case = TradingStatsUseCase(
                grid_repository=self.grid_repository,
                exchange_service=self.exchange_service,
                grid_calculator=self.grid_calculator
            )
            
            logger.info("✅ Servicios de Grid y casos de uso inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando servicios: {e}")
            raise

    def _setup_jobs(self):
        """Configura los trabajos del scheduler."""
        try:
            # 🚀 TRABAJO PRINCIPAL: Monitor en tiempo real (cada 10 segundos)
            self.scheduler.add_job(
                func=self._run_realtime_monitor,
                trigger=IntervalTrigger(seconds=REALTIME_MONITOR_INTERVAL_SECONDS),
                id='realtime_grid_monitor',
                name='Real-Time Grid Monitor',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=5  # 5 segundos de gracia
            )
            
            # ⏰ TRABAJO HORARIO: Gestión de transiciones
            self.scheduler.add_job(
                func=self._run_hourly_management,
                trigger=IntervalTrigger(hours=MONITORING_INTERVAL_HOURS),
                id='hourly_grid_management',
                name='Hourly Grid Management',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300  # 5 minutos de gracia
            )
            
            logger.info("✅ Trabajos configurados:")
            logger.info(f"  ⚡ Monitor tiempo real: cada {REALTIME_MONITOR_INTERVAL_SECONDS} segundos")
            logger.info(f"  ⏰ Gestión horaria: cada {MONITORING_INTERVAL_HOURS} hora(s)")
            
        except Exception as e:
            logger.error(f"❌ Error configurando trabajos del scheduler: {e}")
            raise

    def _run_realtime_monitor(self):
        """
        ⚡ MONITOR EN TIEMPO REAL (cada 10 segundos):
        - Detecta fills inmediatamente
        - Crea órdenes complementarias al instante
        - Optimizado para aprovechar volatilidad
        """
        try:
            result = self.realtime_monitor_use_case.execute()
            
            # Solo loggear si hubo actividad (evitar spam de logs)
            if result.get('fills_detected', 0) > 0 or result.get('orders_created', 0) > 0:
                fills = result.get('fills_detected', 0)
                orders = result.get('orders_created', 0)
                trades = result.get('trades_completed', 0)
                logger.info(f"⚡ RT: {fills} fills, {orders} órdenes nuevas, {trades} trades")
                
        except Exception as e:
            logger.error(f"❌ Error en monitor tiempo real: {e}")
            # No enviar notificación por errores de tiempo real para evitar spam

    def _run_hourly_management(self):
        """
        ⏰ GESTIÓN HORARIA:
        1. Gestión de transiciones (pausar/activar según Cerebro)
        2. Limpieza de cache del monitor tiempo real
        3. Sincronización de estados
        """
        try:
            logger.info("🔄 ========== GESTIÓN HORARIA DE GRID TRADING ==========")
            
            # PASO 1: Gestionar transiciones de estado
            logger.info("🔧 PASO 1: Gestionando transiciones de estado...")
            transition_result = self.transition_use_case.execute()
            
            activations = transition_result.get('activations', 0)
            pauses = transition_result.get('pauses', 0)
            
            if transition_result.get('success', False):
                logger.info(f"✅ Transiciones: {activations} activaciones, {pauses} pausas")
            else:
                error = transition_result.get('error', 'Error desconocido')
                logger.error(f"❌ Error en transiciones: {error}")
            
            # PASO 2: Limpiar cache del monitor tiempo real
            logger.info("🧹 PASO 2: Limpiando cache del monitor tiempo real...")
            self.realtime_monitor_use_case.clear_cache()
            
            # PASO 3: Verificar cambios de decisión y enviar notificaciones
            logger.info("📊 PASO 3: Verificando cambios de decisión...")
            configs_with_decisions = self.trading_stats_use_case.get_decision_changes()
            self.notification_service.send_decision_change_notification(configs_with_decisions)
            
            # PASO 4: Generar y enviar resumen periódico de trading
            logger.info("📊 PASO 4: Generando resumen periódico de trading...")
            trading_summary = self.trading_stats_use_case.generate_trading_summary()
            self.notification_service.send_periodic_trading_summary(trading_summary)
            
            active_configs = self.grid_repository.get_active_configs()
            total_active_bots = len(active_configs)
                
            logger.info(f"✅ Gestión horaria completada: {total_active_bots} bots activos")
            logger.info("✅ ========== GESTIÓN HORARIA COMPLETADA ==========")
            
        except Exception as e:
            logger.error(f"❌ Error en gestión horaria: {e}")
            self.notification_service.send_error_notification("Grid Hourly Management", str(e))

    def start(self):
        """Inicia el scheduler híbrido."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("✅ Grid Scheduler híbrido iniciado")
                logger.info("  ⚡ Monitor tiempo real: cada 10 segundos")
                logger.info(f"  ⏰ Gestión horaria: cada {MONITORING_INTERVAL_HOURS} hora(s)")
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
                "monitoring_interval_hours": MONITORING_INTERVAL_HOURS,
                "realtime_interval_seconds": REALTIME_MONITOR_INTERVAL_SECONDS
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del scheduler: {e}")
            return {"status": "error", "error": str(e)}

    def trigger_manual_monitoring(self):
        """Ejecuta manualmente la gestión horaria (útil para comandos de Telegram)."""
        try:
            logger.info("🔧 Ejecutando gestión horaria manual...")
            self._run_hourly_management()
            return {"success": True, "message": "Gestión horaria manual ejecutada"}
            
        except Exception as e:
            logger.error(f"❌ Error en gestión horaria manual: {e}")
            return {"success": False, "error": str(e)}
            
    def trigger_realtime_check(self):
        """Ejecuta manualmente el monitor tiempo real (útil para testing)."""
        try:
            logger.info("⚡ Ejecutando monitor tiempo real manual...")
            self._run_realtime_monitor()
            return {"success": True, "message": "Monitor tiempo real manual ejecutado"}
            
        except Exception as e:
            logger.error(f"❌ Error en monitor tiempo real manual: {e}")
            return {"success": False, "error": str(e)} 