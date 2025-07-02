"""
Trend Scheduler - Maneja la ejecución periódica del Trend Bot
Consulta al cerebro cada hora para decisiones de trading de tendencias.
"""

import threading
from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.services.logging_config import get_logger
from shared.database.session import get_db_session
from shared.database.models import GridBotConfig, EstrategiaStatus
from services.trend.core.trading_engine import run_trend_trading_bot
# El cerebro enviará las decisiones directamente

logger = get_logger(__name__)


class TrendScheduler:
    """
    Scheduler para el Trend Trading Bot.
    Ejecuta la estrategia de tendencias consultando al cerebro periódicamente.
    """
    
    def __init__(self):
        """Inicializa el scheduler de trend."""
        self.scheduler = BackgroundScheduler(daemon=True)
        self.active_bots: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        
        # Configurar scheduler
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Configura los jobs del scheduler"""
        try:
            # Verificación del cerebro cada hora para trend trading
            self.scheduler.add_job(
                func=self.check_trend_decisions,
                trigger=IntervalTrigger(hours=1),
                id='trend_cerebro_check',
                name='Trend Cerebro Check',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=60
            )
            
            logger.info("✅ Trend Scheduler configurado correctamente")
            logger.info("🧠 Consulta al cerebro programada cada 1 hora")
            
        except Exception as e:
            logger.error(f"❌ Error configurando Trend Scheduler: {e}")
            raise
    
    def start(self):
        """Inicia el scheduler de trend"""
        try:
            if self.scheduler.running:
                logger.info("✅ Trend Scheduler ya está ejecutándose")
                return
            
            self.scheduler.start()
            logger.info("✅ Trend Scheduler iniciado")
            logger.info("📈 Sistema de tendencias activado")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Trend Scheduler: {e}")
            raise
    
    def stop(self):
        """Detiene el scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Trend Scheduler detenido")
                
        except Exception as e:
            logger.error(f"❌ Error deteniendo Trend Scheduler: {e}")
    
    def check_trend_decisions(self):
        """
        Consulta las decisiones del cerebro para trend trading.
        Este método se ejecuta cada hora.
        """
        try:
            logger.info("🧠 ========== CONSULTANDO CEREBRO PARA TREND TRADING ==========")
            
            # Obtener configuraciones activas con estrategia TREND
            with get_db_session() as db:
                # Por ahora solo ETH/USDT tiene estrategia TREND
                configs = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == 'ETH/USDT',
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                ).all()
                
                if not configs:
                    logger.warning("⚠️ No hay configuraciones activas para trend trading")
                    return
                
                for config_db in configs:
                    # Verificar que existe estrategia TREND para este par
                    estrategia = db.query(EstrategiaStatus).filter(
                        EstrategiaStatus.par == config_db.pair,
                        EstrategiaStatus.estrategia == "TREND"
                    ).order_by(EstrategiaStatus.timestamp.desc()).first()
                    
                    if not estrategia:
                        logger.info(f"ℹ️ No hay estrategia TREND para {config_db.pair}")
                        continue
                    
                    # Preparar configuración
                    config = {
                        'pair': config_db.pair,
                        'total_capital': config_db.total_capital,
                        'telegram_chat_id': config_db.telegram_chat_id,
                        'cerebro_decision': estrategia.decision,
                        'indicadores': estrategia.indicadores if hasattr(estrategia, 'indicadores') else {}
                    }
                    
                    logger.info(f"📊 Procesando {config['pair']} - Decisión: {config['cerebro_decision']}")
                    
                    # Ejecutar el bot de tendencias
                    self._execute_trend_bot(config)
                    
        except Exception as e:
            logger.error(f"❌ Error en verificación de decisiones trend: {e}")
    
    def _execute_trend_bot(self, config: Dict[str, Any]):
        """
        Ejecuta el bot de tendencias con la configuración dada.
        
        Args:
            config: Configuración del bot incluyendo decisión del cerebro
        """
        try:
            pair = config['pair']
            decision = config.get('cerebro_decision', 'MANTENER_ESPERA')
            
            logger.info(f"🤖 Ejecutando Trend Bot para {pair} - Decisión: {decision}")
            
            # Ejecutar el motor de trading
            run_trend_trading_bot(config)
            
            logger.info(f"✅ Trend Bot ejecutado para {pair}")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trend bot para {config.get('pair')}: {e}")
    
    def force_check_now(self):
        """
        Fuerza una verificación inmediata del cerebro.
        Útil para testing o comandos manuales.
        """
        try:
            logger.info("🔄 Forzando verificación inmediata del cerebro para trend...")
            self.check_trend_decisions()
            
        except Exception as e:
            logger.error(f"❌ Error en verificación forzada: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del scheduler"""
        return {
            'scheduler_running': self.scheduler.running,
            'next_check': self._get_next_run_time(),
            'strategy': 'TREND',
            'check_interval': '1 hora',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_next_run_time(self) -> Optional[str]:
        """Obtiene la próxima hora de ejecución"""
        try:
            job = self.scheduler.get_job('trend_cerebro_check')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
            return None
        except Exception:
            return None


# Instancia global del scheduler
_trend_scheduler: Optional[TrendScheduler] = None


def get_trend_scheduler() -> TrendScheduler:
    """Obtiene la instancia global del scheduler de trend"""
    global _trend_scheduler
    if _trend_scheduler is None:
        _trend_scheduler = TrendScheduler()
    return _trend_scheduler


def start_trend_scheduler():
    """Inicia el scheduler de trend"""
    try:
        scheduler = get_trend_scheduler()
        scheduler.start()
        return True
    except Exception as e:
        logger.error(f"❌ Error iniciando trend scheduler: {e}")
        return False


def stop_trend_scheduler():
    """Detiene el scheduler de trend"""
    try:
        scheduler = get_trend_scheduler()
        scheduler.stop()
        return True
    except Exception as e:
        logger.error(f"❌ Error deteniendo trend scheduler: {e}")
        return False


__all__ = [
    'TrendScheduler',
    'get_trend_scheduler',
    'start_trend_scheduler',
    'stop_trend_scheduler'
] 