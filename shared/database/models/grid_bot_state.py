"""
Modelo para almacenar el estado actual del bot de grid trading V2.
Incluye tracking de estrategias avanzadas y métricas de performance.
"""
from sqlalchemy import Column, Integer, Boolean, DateTime, Float
from datetime import datetime
from .base import Base


class GridBotState(Base):
    """
    Modelo para almacenar el estado actual del bot de grid trading V2.
    Incluye tracking de estrategias avanzadas y métricas de performance.
    Permite persistir el estado entre reinicios y hacer tracking del bot.
    """
    __tablename__ = "grid_bot_state"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, nullable=False)  # Referencia a GridBotConfig
    is_running = Column(Boolean, default=False)
    
    # Trading metrics
    last_execution = Column(DateTime, nullable=True)
    total_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    current_price = Column(Float, nullable=True)
    active_orders_count = Column(Integer, default=0)
    
    # Grid boundaries tracking
    lowest_buy_price = Column(Float, nullable=True)  # Para calcular stop-loss
    highest_sell_price = Column(Float, nullable=True)  # Para calcular trailing up
    
    # Advanced strategies tracking
    stop_loss_triggered_count = Column(Integer, default=0)
    trailing_up_triggered_count = Column(Integer, default=0)
    last_grid_adjustment = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 