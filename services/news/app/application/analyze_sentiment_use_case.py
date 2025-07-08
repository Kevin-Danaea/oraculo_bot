"""
Caso de uso para analizar el sentimiento de las noticias.
"""
from typing import Optional
from dataclasses import dataclass
import time

from app.domain.interfaces import NewsRepository, SentimentAnalyzer
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


@dataclass
class AnalyzeSentimentResult:
    """Resultado del caso de uso de análisis de sentimiento."""
    success: bool
    analyzed_posts: int
    message: str
    error: Optional[str] = None


class AnalyzeSentimentUseCase:
    """
    Caso de uso para analizar el sentimiento de las noticias.
    MEJORADO: Con retry logic y mejor manejo de errores de transacción.
    """
    
    def __init__(self,
                 sentiment_analyzer: SentimentAnalyzer,
                 news_repository: NewsRepository):
        self.sentiment_analyzer = sentiment_analyzer
        self.news_repository = news_repository
    
    def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0):
        """
        Ejecuta una operación con reintentos en caso de error.
        
        Args:
            operation: Función a ejecutar
            max_retries: Número máximo de reintentos
            delay: Delay entre reintentos en segundos
            
        Returns:
            Resultado de la operación
        """
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Intento {attempt + 1} falló: {e}. Reintentando en {delay}s...")
                time.sleep(delay)
                delay *= 2  # Backoff exponencial
    
    def _analyze_single_news(self, news) -> bool:
        """
        Analiza una sola noticia con manejo robusto de errores.
        
        Args:
            news: Entidad de noticia a analizar
            
        Returns:
            True si se analizó exitosamente, False en caso contrario
        """
        try:
            # Verificar que la noticia tenga ID
            if news.id is None:
                logger.error(f"Noticia sin ID encontrada: {news.headline[:30] if news.headline else 'Sin título'}...")
                return False
            
            # Analizar sentimiento con retry
            def analyze_text():
                return self.sentiment_analyzer.analyze_text(news.headline)
            
            analysis = self._retry_operation(analyze_text)
            
            if analysis is None:
                logger.error(f"Análisis retornó None para noticia {news.id}")
                return False
            
            # Actualizar noticia con análisis con retry
            def update_analysis():
                return self.news_repository.update_sentiment_analysis(news.id, analysis)
            
            self._retry_operation(update_analysis)
            
            logger.info(
                f"📊 Noticia analizada: '{news.headline[:50] if news.headline else 'Sin título'}...' → "
                f"Score: {analysis.sentiment_score:.2f}, "
                f"Emoción: {analysis.primary_emotion.value}, "
                f"Categoría: {analysis.news_category.value}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error analizando noticia {news.id}: {e}")
            return False
    
    def execute(self) -> AnalyzeSentimentResult:
        """
        Ejecuta el análisis de sentimiento de noticias no analizadas.
        """
        try:
            logger.info("🧠 Iniciando análisis de sentimiento...")
            
            # Obtener noticias sin analizar con retry
            def get_unanalyzed():
                return self.news_repository.find_unanalyzed(limit=500)
            
            unanalyzed_news = self._retry_operation(get_unanalyzed)
            
            if not unanalyzed_news:
                return AnalyzeSentimentResult(
                    success=True,
                    analyzed_posts=0,
                    message="No hay noticias nuevas para analizar"
                )
            
            logger.info(f"🧠 Analizando {len(unanalyzed_news)} noticias...")
            analyzed_count = 0
            error_count = 0
            
            for i, news in enumerate(unanalyzed_news, 1):
                try:
                    if self._analyze_single_news(news):
                        analyzed_count += 1
                    else:
                        error_count += 1
                        
                    # Log progreso cada 10 noticias
                    if i % 10 == 0:
                        logger.info(f"📊 Progreso: {i}/{len(unanalyzed_news)} noticias procesadas")
                        
                except Exception as e:
                    logger.error(f"Error procesando noticia {i}: {e}")
                    error_count += 1
                    continue
            
            logger.info(f"✅ Análisis completado: {analyzed_count} exitosos, {error_count} errores")
            
            return AnalyzeSentimentResult(
                success=True,
                analyzed_posts=analyzed_count,
                message=f"✅ Análisis completado: {analyzed_count} noticias procesadas"
            )
            
        except Exception as e:
            logger.error(f"💥 Error en análisis de sentimientos: {e}")
            return AnalyzeSentimentResult(
                success=False,
                analyzed_posts=0,
                message="Error en análisis",
                error=str(e)
            ) 