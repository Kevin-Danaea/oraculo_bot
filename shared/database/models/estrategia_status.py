"""
Modelo para almacenar el estado de las estrategias de trading.
Registra decisiones del cerebro de trading y sus indicadores.
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from datetime import datetime
from .base import Base


class EstrategiaStatus(Base):
    """
    Modelo para almacenar el estado de las estrategias de trading.
    """
    __tablename__ = "estrategia_status"

    id = Column(Integer, primary_key=True, index=True)
    par = Column(String, nullable=False, index=True)  # Ej: "ETH/USDT"
    estrategia = Column(String, nullable=False)  # Ej: "GRID"
    decision = Column(String, nullable=False)  # "OPERAR_GRID" o "PAUSAR_GRID"
    razon = Column(Text, nullable=True)  # Razón de la decisión
    
    # Indicadores utilizados para la decisión
    adx_actual = Column(Float, nullable=True)
    volatilidad_actual = Column(Float, nullable=True)
    sentiment_promedio = Column(Float, nullable=True)
    
    # Indicadores específicos para TREND
    sma30_actual = Column(Float, nullable=True)
    sma150_actual = Column(Float, nullable=True)
    sentiment_7d_avg = Column(Float, nullable=True)
    
    # Umbrales utilizados
    umbral_adx = Column(Float, nullable=True)
    umbral_volatilidad = Column(Float, nullable=True)
    umbral_sentimiento = Column(Float, nullable=True)
    
    # Umbrales específicos para TREND
    umbral_adx_trend = Column(Float, nullable=True)
    umbral_sentiment_trend = Column(Float, nullable=True)
    
    # Señales específicas para TREND
    golden_cross = Column(Boolean, default=False, nullable=True)
    death_cross = Column(Boolean, default=False, nullable=True)
    trend_strength_ok = Column(Boolean, default=False, nullable=True)
    sentiment_ok = Column(Boolean, default=False, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario para logging y API responses"""
        return {
            'id': self.id,
            'par': self.par,
            'estrategia': self.estrategia,
            'decision': self.decision,
            'razon': self.razon,
            'adx_actual': self.adx_actual,
            'volatilidad_actual': self.volatilidad_actual,
            'sentiment_promedio': self.sentiment_promedio,
            'sma30_actual': self.sma30_actual,
            'sma150_actual': self.sma150_actual,
            'sentiment_7d_avg': self.sentiment_7d_avg,
            'umbral_adx': self.umbral_adx,
            'umbral_volatilidad': self.umbral_volatilidad,
            'umbral_sentimiento': self.umbral_sentimiento,
            'umbral_adx_trend': self.umbral_adx_trend,
            'umbral_sentiment_trend': self.umbral_sentiment_trend,
            'golden_cross': self.golden_cross,
            'death_cross': self.death_cross,
            'trend_strength_ok': self.trend_strength_ok,
            'sentiment_ok': self.sentiment_ok,
            'timestamp': self.timestamp.isoformat() if self.timestamp is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        } 