"""
Servicios específicos del microservicio de noticias.
Incluye recopilación de Reddit, CryptoPanic y análisis de sentimientos.
"""

# Importar servicios para hacerlos disponibles
from . import reddit_service
from . import sentiment_service
from . import cryptopanic_service

__all__ = ['reddit_service', 'sentiment_service', 'cryptopanic_service'] 