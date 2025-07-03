"""
Entidades de dominio para el servicio de noticias.
Representan los conceptos centrales del negocio sin dependencias externas.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class EmotionType(str, Enum):
    """Tipos de emociones válidas para el análisis de sentimiento."""
    EUFORIA = "Euforia"
    OPTIMISMO = "Optimismo"
    NEUTRAL = "Neutral"
    INCERTIDUMBRE = "Incertidumbre"
    MIEDO = "Miedo"


class CategoryType(str, Enum):
    """Categorías válidas para clasificar las noticias."""
    REGULACION = "Regulación"
    TECNOLOGIA_ADOPCION = "Tecnología/Adopción"
    MERCADO_TRADING = "Mercado/Trading"
    SEGURIDAD = "Seguridad"
    MACROECONOMIA = "Macroeconomía"


@dataclass
class News:
    """
    Entidad principal que representa una noticia de criptomonedas.
    """
    id: Optional[int]
    source: str
    headline: str
    url: str
    published_at: datetime
    sentiment_score: Optional[float] = None
    primary_emotion: Optional[EmotionType] = None
    news_category: Optional[CategoryType] = None
    
    def __post_init__(self):
        """Validaciones de dominio."""
        if self.sentiment_score is not None:
            if not -1.0 <= self.sentiment_score <= 1.0:
                raise ValueError("El sentiment_score debe estar entre -1.0 y 1.0")
        
        if self.url and not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("La URL debe comenzar con http:// o https://")
    
    def is_analyzed(self) -> bool:
        """Verifica si la noticia ya fue analizada."""
        return self.sentiment_score is not None
    
    def is_from_reddit(self) -> bool:
        """Verifica si la noticia proviene de Reddit."""
        return "Reddit" in self.source
    
    def is_community_post(self) -> bool:
        """Verifica si es un post de la comunidad."""
        return "Community Post" in self.source
    
    def is_news_link(self) -> bool:
        """Verifica si es un enlace a una noticia externa."""
        return self.is_from_reddit() and not self.is_community_post()


@dataclass
class SentimentAnalysis:
    """
    Resultado del análisis de sentimiento de una noticia.
    """
    sentiment_score: float
    primary_emotion: EmotionType
    news_category: CategoryType
    
    def __post_init__(self):
        """Validaciones del análisis."""
        if not -1.0 <= self.sentiment_score <= 1.0:
            raise ValueError("El sentiment_score debe estar entre -1.0 y 1.0")
    
    def is_positive(self) -> bool:
        """Determina si el sentimiento es positivo."""
        return self.sentiment_score > 0.1
    
    def is_negative(self) -> bool:
        """Determina si el sentimiento es negativo."""
        return self.sentiment_score < -0.1
    
    def is_neutral(self) -> bool:
        """Determina si el sentimiento es neutral."""
        return -0.1 <= self.sentiment_score <= 0.1 