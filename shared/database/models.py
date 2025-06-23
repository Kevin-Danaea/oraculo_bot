"""
Modelos de base de datos compartidos entre todos los microservicios.
Define la estructura de tablas para sentimientos y análisis.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Noticia(Base):
    """
    Modelo para almacenar noticias recopiladas y su análisis de sentimientos.
    Utilizado por el servicio de noticias y consultado por otros servicios.
    """
    __tablename__ = "noticias"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    headline = Column(Text, nullable=False)
    url = Column(String, unique=True, index=True)
    published_at = Column(String, nullable=False)
    sentiment_score = Column(Float, nullable=True)  # Se llenará en fases futuras
    entities = Column(Text, nullable=True)          # Se llenará en fases futuras


class GridBotConfig(Base):
    """
    Modelo para almacenar la configuración del bot de grid trading.
    Permite gestionar la configuración dinámicamente sin necesidad de redeploys.
    """
    __tablename__ = "grid_bot_config"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, nullable=False)  # Ej: "ETH/USDT"
    total_capital = Column(Float, nullable=False)
    grid_levels = Column(Integer, nullable=False)
    price_range_percent = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    telegram_chat_id = Column(String, nullable=True)  # Chat ID específico del usuario
    
    def to_dict(self):
        """Convierte el objeto a diccionario para usar en el trading engine"""
        return {
            'pair': self.pair,
            'total_capital': self.total_capital,
            'grid_levels': self.grid_levels,
            'price_range_percent': self.price_range_percent
        }


class GridBotState(Base):
    """
    Modelo para almacenar el estado actual del bot de grid trading.
    Permite persistir el estado entre reinicios y hacer tracking del bot.
    """
    __tablename__ = "grid_bot_state"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, nullable=False)  # Referencia a GridBotConfig
    is_running = Column(Boolean, default=False)
    last_execution = Column(DateTime, nullable=True)
    total_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    current_price = Column(Float, nullable=True)
    active_orders_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 