"""
Scheduler para el servicio de noticias.
Gestiona la ejecución periódica del pipeline de recolección y análisis.
"""
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

from app.application.news_pipeline_use_case import NewsPipelineUseCase
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class NewsScheduler:
    """
    Gestiona la programación y ejecución periódica del pipeline de noticias.
    """
    
    def __init__(self, pipeline_use_case: NewsPipelineUseCase):
        self.pipeline_use_case = pipeline_use_case
        self._scheduler: Optional[BackgroundScheduler] = None
    
    def _run_pipeline_job(self):
        """
        Ejecuta el pipeline de noticias como un job del scheduler.
        """
        logger.info("🚀 Ejecutando job del pipeline de noticias...")
        try:
            result = self.pipeline_use_case.execute()
            
            if result['pipeline_success']:
                logger.info("✅ Pipeline ejecutado exitosamente")
                
                # Log detalles de recolección
                if result.get('collection_result'):
                    collection = result['collection_result']
                    logger.info(f"   📰 Noticias nuevas: {collection.new_posts}")
                
                # Log detalles de análisis
                if result.get('analysis_result'):
                    analysis = result['analysis_result']
                    logger.info(f"   🧠 Noticias analizadas: {analysis.analyzed_posts}")
            else:
                logger.error("❌ Pipeline ejecutado con errores")
                
        except Exception as e:
            logger.error(f"💥 Error ejecutando pipeline: {e}")
    
    def setup(self) -> 'NewsScheduler':
        """
        Configura el scheduler con las tareas programadas.
        
        Returns:
            Self para encadenamiento
        """
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler()
            
            # Programar pipeline unificado cada hora
            self._scheduler.add_job(
                self._run_pipeline_job,
                'interval',
                hours=1,
                id='news_pipeline',
                name='News Collection and Sentiment Analysis',
                misfire_grace_time=300  # 5 minutos de gracia si se pierde la ejecución
            )
            
            logger.info("✅ Scheduler configurado: Pipeline cada hora")
        
        return self
    
    def start(self):
        """Inicia el scheduler."""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("✅ News scheduler iniciado")
            
            # Ejecutar inmediatamente el primer pipeline
            logger.info("🚀 Ejecutando pipeline inicial...")
            self._run_pipeline_job()
    
    def stop(self):
        """Detiene el scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("✅ News scheduler detenido")
            self._scheduler = None
    
    @property
    def is_running(self) -> bool:
        """Verifica si el scheduler está en ejecución."""
        return self._scheduler is not None and self._scheduler.running
    
    def get_jobs_count(self) -> int:
        """Obtiene el número de jobs activos."""
        if self._scheduler:
            return len(self._scheduler.get_jobs())
        return 0 