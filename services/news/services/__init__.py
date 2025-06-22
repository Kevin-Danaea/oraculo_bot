"""
Servicios específicos del microservicio de noticias.
Incluye recopilación de Reddit y análisis de sentimientos.
"""

# Importar servicios activos
from . import reddit_service
from . import sentiment_service

__all__ = ['reddit_service', 'sentiment_service'] 