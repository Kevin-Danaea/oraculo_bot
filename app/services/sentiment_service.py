# Compatibilidad hacia atrás: importar desde services/news
# TODO: Remover este archivo una vez completada la migración
from services.news.services.sentiment_service import analyze_sentiment, analyze_sentiment_text

# Re-exportar para compatibilidad
__all__ = ['analyze_sentiment', 'analyze_sentiment_text'] 