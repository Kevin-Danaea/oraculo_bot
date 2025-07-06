"""
Interfaces del dominio (puertos) que definen contratos para las dependencias externas.
Estas interfaces serán implementadas en la capa de infraestructura.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from .entities import News, SentimentAnalysis


class NewsRepository(ABC):
    """
    Puerto para el repositorio de noticias.
    Define las operaciones de persistencia necesarias.
    """
    
    @abstractmethod
    def save(self, news: News) -> News:
        """Guarda una noticia en el repositorio."""
        pass
    
    @abstractmethod
    def save_many(self, news_list: List[News]) -> List[News]:
        """Guarda múltiples noticias de forma eficiente."""
        pass
    
    @abstractmethod
    def find_by_url(self, url: str) -> Optional[News]:
        """Busca una noticia por su URL."""
        pass
    
    @abstractmethod
    def find_unanalyzed(self, limit: int = 500) -> List[News]:
        """Obtiene noticias que no han sido analizadas."""
        pass
    
    @abstractmethod
    def update_sentiment_analysis(self, news_id: int, analysis: SentimentAnalysis) -> News:
        """Actualiza el análisis de sentimiento de una noticia."""
        pass


class NewsCollector(ABC):
    """
    Puerto para el servicio de recolección de noticias.
    Define cómo obtener noticias de fuentes externas.
    """
    
    @abstractmethod
    def collect_news(self) -> List[Dict[str, Any]]:
        """
        Recolecta noticias desde la fuente externa.
        Retorna una lista de diccionarios con datos crudos.
        """
        pass


class SentimentAnalyzer(ABC):
    """
    Puerto para el servicio de análisis de sentimientos.
    Define cómo analizar el sentimiento de un texto.
    """
    
    @abstractmethod
    def analyze_text(self, text: str) -> SentimentAnalysis:
        """
        Analiza el sentimiento de un texto.
        Retorna un objeto SentimentAnalysis con los resultados.
        """
        pass


class NotificationService(ABC):
    """
    Puerto para el servicio de notificaciones.
    Define cómo enviar notificaciones sobre el estado del servicio.
    """
    
    @abstractmethod
    def send_startup_notification(self, service_name: str, features: List[str]) -> None:
        """Envía una notificación cuando el servicio se inicia."""
        pass
    
    @abstractmethod
    def send_error_notification(self, service_name: str, error: str) -> None:
        """Envía una notificación cuando ocurre un error."""
        pass 