"""
Caso de uso para ejecutar el pipeline completo de noticias.
"""
from typing import Dict, Any

from app.application.collect_news_use_case import CollectNewsUseCase
from app.application.analyze_sentiment_use_case import AnalyzeSentimentUseCase
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class NewsPipelineUseCase:
    """
    Caso de uso para ejecutar el pipeline completo de noticias.
    Combina recolección y análisis en un flujo unificado.
    """
    
    def __init__(self,
                 collect_news_use_case: CollectNewsUseCase,
                 analyze_sentiment_use_case: AnalyzeSentimentUseCase):
        self.collect_news = collect_news_use_case
        self.analyze_sentiment = analyze_sentiment_use_case
    
    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo: recolección + análisis.
        """
        logger.info("🚀 Iniciando pipeline de noticias: Recolección y Análisis.")
        
        results = {
            'pipeline_success': True,
            'collection_result': None,
            'analysis_result': None
        }
        
        try:
            # Paso 1: Recolectar noticias
            logger.info("📰 Paso 1: Recolectando noticias...")
            collection_result = self.collect_news.execute()
            results['collection_result'] = collection_result
            
            if not collection_result.success:
                results['pipeline_success'] = False
                logger.error(f"❌ Error en recolección: {collection_result.error}")
                return results
            
            logger.info(f"✅ Recolección completada: {collection_result.message}")
            
            # Paso 2: Analizar sentimientos
            logger.info("🧠 Paso 2: Analizando sentimientos...")
            analysis_result = self.analyze_sentiment.execute()
            results['analysis_result'] = analysis_result
            
            if not analysis_result.success:
                results['pipeline_success'] = False
                logger.error(f"❌ Error en análisis: {analysis_result.error}")
                return results
            
            logger.info(f"✅ Análisis completado: {analysis_result.message}")
            
        except Exception as e:
            logger.error(f"💥 Error inesperado en el pipeline: {e}")
            results['pipeline_success'] = False
            results['error'] = str(e)
        
        logger.info("🏁 Pipeline de noticias finalizado.")
        return results 