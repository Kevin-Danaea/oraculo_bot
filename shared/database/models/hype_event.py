"""
Modelo para registrar eventos de hype detectados por el Hype Radar.
Almacena alertas de tendencias significativas en memecoins/altcoins.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from datetime import datetime
from .base import Base


class HypeEvent(Base):
    """
    Modelo para registrar eventos de hype detectados por el Hype Radar.
    Almacena alertas de tendencias significativas en memecoins/altcoins.
    """
    __tablename__ = "hype_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)  # Ej: "DOGE", "SHIB"
    mention_increase_percent = Column(Float, nullable=False)  # % de incremento de menciones
    triggering_post_title = Column(Text, nullable=True)  # Título del post que disparó la alerta
    
    # Datos adicionales del análisis
    current_mentions = Column(Integer, nullable=False)  # Menciones en la última hora
    avg_mentions = Column(Float, nullable=False)  # Promedio histórico de 24h
    threshold_used = Column(Float, nullable=False)  # Umbral utilizado para la alerta
    
    # Metadatos de la fuente
    source_subreddit = Column(String, nullable=True)  # Subreddit donde se detectó el hype
    alert_sent = Column(Boolean, default=False)  # Si se envió alerta por Telegram
    alert_level = Column(String, nullable=True)  # "NORMAL", "HIGH", "EXTREME"
    
    # Timestamps de control
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario para logging y API responses"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp is not None else None,
            'ticker': self.ticker,
            'mention_increase_percent': self.mention_increase_percent,
            'triggering_post_title': self.triggering_post_title,
            'current_mentions': self.current_mentions,
            'avg_mentions': self.avg_mentions,
            'threshold_used': self.threshold_used,
            'source_subreddit': self.source_subreddit,
            'alert_sent': self.alert_sent,
            'alert_level': self.alert_level,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None
        } 