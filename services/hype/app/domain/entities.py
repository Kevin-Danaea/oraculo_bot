"""
Define las entidades del dominio para el servicio de Hype.

Estas clases son representaciones de los objetos de negocio principales,
independientes de la capa de persistencia o de la API.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class Post(BaseModel):
    """Representa un post individual de una fuente como Reddit."""
    id: str
    title: str
    url: str
    subreddit: str
    created_utc: datetime


class TickerMention(BaseModel):
    """Representa una mención agregada de un ticker en un escaneo."""
    ticker: str
    count: int


# Representa una alerta de Hype generada por el sistema.
# Esta entidad se persistirá en la base de datos para consultas de eventos.
class HypeEvent(BaseModel):
    """Un evento de Hype discreto que ha superado el umbral de alerta."""
    id: Optional[int] = None
    ticker: str
    mentions_24h: int
    threshold: int
    alert_sent: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Representa el resultado completo de un ciclo de escaneo.
# Se usa para análisis histórico y para guardar los datos brutos.
class HypeScan(BaseModel):
    """Resultado agregado de un escaneo completo de todas las fuentes."""
    id: Optional[int] = None
    scan_timestamp: datetime = Field(default_factory=datetime.utcnow)
    subreddits_scanned: int
    posts_analyzed: int
    total_posts_with_mentions: int
    unique_tickers_mentioned: int
    top_trending_tickers: Dict[str, int]
    mentions: List[TickerMention] = []