"""
Define las interfaces (contratos) para la capa de aplicación.

Estas clases abstractas definen los métodos que las implementaciones concretas
en la capa de infraestructura deben proporcionar.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .entities import HypeEvent, HypeScan, Post

class HypeCollector(ABC):
    """Interfaz para un colector de datos de hype (ej. Reddit)."""
    
    @abstractmethod
    def collect_posts(self, source_name: str) -> List[Post]:
        """
        Colecciona posts recientes de una fuente específica (ej. un subreddit).
        
        Args:
            source_name: El nombre de la fuente (ej. 'CryptoMoonShots').
            
        Returns:
            Una lista de entidades Post.
        """
        pass

    @abstractmethod
    def extract_tickers_from_text(self, text: str) -> List[str]:
        """
        Extrae tickers de un texto. La implementación puede variar por colector.
        """
        pass

class HypeRepository(ABC):
    """Interfaz para la persistencia de datos de hype."""

    @abstractmethod
    def save_scan(self, scan_data: HypeScan) -> HypeScan:
        """Guarda el resultado de un escaneo completo."""
        pass
    
    @abstractmethod
    def save_event(self, event_data: HypeEvent) -> HypeEvent:
        """Guarda un evento de Hype (alerta)."""
        pass

    @abstractmethod
    def get_recent_events(self, hours: int, limit: int) -> List[HypeEvent]:
        """Obtiene los eventos de Hype más recientes."""
        pass

class NotificationService(ABC):
    """Interfaz para un servicio de notificación (ej. Telegram)."""

    @abstractmethod
    def send_alert(self, event: HypeEvent) -> bool:
        """
        Envía una notificación de alerta de Hype.
        
        Args:
            event: El evento de Hype que generó la alerta.
            
        Returns:
            True si la notificación se envió con éxito, False en caso contrario.
        """
        pass

    @abstractmethod
    def send_startup_notification(self, service_name: str, features: List[str]) -> None:
        """Envía una notificación de inicio de servicio."""
        pass

    @abstractmethod
    def send_error_notification(self, service_name: str, error: str) -> None:
        """Envía una notificación de error."""
        pass

    @abstractmethod
    def send_daily_summary(self, summary_stats: Dict[str, Any]) -> bool:
        """Envía el resumen diario de tendencias."""
        pass

class HypeAnalyzer(ABC):
    """Interfaz para el componente de análisis de tendencias de hype."""

    @abstractmethod
    def analyze_mentions(self, ticker_mentions: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Analiza un conjunto de menciones de tickers y genera alertas.
        
        Args:
            ticker_mentions: Un diccionario con tickers y su número de menciones.
            
        Returns:
            Una lista de diccionarios, donde cada uno representa una alerta a enviar.
        """
        pass
    
    @abstractmethod
    def configure_threshold(self, new_threshold: int) -> None:
        """
        Configura un nuevo umbral para la detección de alertas.
        
        Args:
            new_threshold: El nuevo valor para el umbral.
        """
        pass 