"""
Caso de uso para analizar el sentimiento de las noticias.
"""
from typing import Optional
from dataclasses import dataclass

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
    """
    
    def __init__(self,
                 sentiment_analyzer: SentimentAnalyzer,
                 news_repository: NewsRepository):
        self.sentiment_analyzer = sentiment_analyzer
        self.news_repository = news_repository
    
    def execute(self) -> AnalyzeSentimentResult:
        """
        Ejecuta el análisis de sentimiento de noticias no analizadas.
        """
        try:
            logger.info("🧠 Iniciando análisis de sentimiento...")
            
            # Obtener noticias sin analizar
            unanalyzed_news = self.news_repository.find_unanalyzed(limit=500)
            
            if not unanalyzed_news:
                return AnalyzeSentimentResult(
                    success=True,
                    analyzed_posts=0,
                    message="No hay noticias nuevas para analizar"
                )
            
            logger.info(f"🧠 Analizando {len(unanalyzed_news)} noticias...")
            analyzed_count = 0
            
            for news in unanalyzed_news:
                try:
                    # Verificar que la noticia tenga ID
                    if news.id is None:
                        logger.error(f"Noticia sin ID encontrada: {news.headline[:30]}...")
                        continue
                    
                    # Analizar sentimiento
                    analysis = self.sentiment_analyzer.analyze_text(news.headline)
                    
                    # Actualizar noticia con análisis
                    self.news_repository.update_sentiment_analysis(
                        news.id,
                        analysis
                    )
                    
                    analyzed_count += 1
                    logger.info(
                        f"📊 [{analyzed_count}/{len(unanalyzed_news)}] "
                        f"'{news.headline[:50]}...' → "
                        f"Score: {analysis.sentiment_score:.2f}, "
                        f"Emoción: {analysis.primary_emotion.value}, "
                        f"Categoría: {analysis.news_category.value}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error analizando noticia {news.id}: {e}")
                    continue
            
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