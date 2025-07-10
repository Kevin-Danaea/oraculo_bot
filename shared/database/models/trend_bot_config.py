"""
Modelo para configuración del bot de trend following.
SISTEMA SIMPLE: Solo configuración básica para ETH/USDT
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .base import Base


class TrendBotConfig(Base):
    """
    Modelo para almacenar la configuración del bot de trend following.
    SISTEMA SIMPLE: Solo configuración básica para ETH/USDT
    """
    __tablename__ = "trend_bot_config"

    id = Column(Integer, primary_key=True, index=True)
    
    # IDENTIFICACIÓN
    telegram_chat_id = Column(String, nullable=False, index=True)  # Chat ID del usuario
    
    # CONFIGURACIÓN BÁSICA
    pair = Column(String, nullable=False, default='ETH/USDT')  # Par de trading
    capital_allocation = Column(Float, nullable=False, default=300.0)  # Capital en USDT
    trailing_stop_percent = Column(Float, nullable=False, default=20.0)  # % de trailing stop
    
    # CONTROL
    is_active = Column(Boolean, default=False)  # Si la configuración está activa
    is_running = Column(Boolean, default=False)  # Si el bot está ejecutándose
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'pair': self.pair,
            'capital_allocation': self.capital_allocation,
            'trailing_stop_percent': self.trailing_stop_percent,
            'is_active': self.is_active,
            'is_running': self.is_running
        }
    
    @classmethod
    def get_default_config(cls) -> dict:
        """
        Obtiene la configuración por defecto para trend following
        
        Returns:
            Diccionario con configuración por defecto
        """
        return {
            'pair': 'ETH/USDT',
            'capital_allocation': 300.0,  # $300 USDT
            'trailing_stop_percent': 20.0,  # 20% trailing stop
        } 