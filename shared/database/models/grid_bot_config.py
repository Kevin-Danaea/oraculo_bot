"""
Modelo para configuración del bot de grid trading V2.
SISTEMA DE 3 CONFIGURACIONES FIJAS: ETH, BTC, AVAX
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .base import Base


class GridBotConfig(Base):
    """
    Modelo para almacenar la configuración del bot de grid trading V2.
    SISTEMA DE 3 CONFIGURACIONES FIJAS: ETH, BTC, AVAX
    Cada usuario tiene 3 configuraciones predefinidas que se actualizan, no se crean nuevas.
    """
    __tablename__ = "grid_bot_config"

    id = Column(Integer, primary_key=True, index=True)
    
    # IDENTIFICACIÓN DE CONFIGURACIÓN
    telegram_chat_id = Column(String, nullable=False, index=True)  # Chat ID del usuario
    config_type = Column(String, nullable=False, index=True)  # 'ETH', 'BTC', 'AVAX'
    
    # CONFIGURACIÓN DE TRADING
    pair = Column(String, nullable=False)  # Ej: "ETH/USDT", "BTC/USDT", "AVAX/USDT"
    total_capital = Column(Float, nullable=False)
    grid_levels = Column(Integer, nullable=False, default=30)  # Fijo: 30
    price_range_percent = Column(Float, nullable=False, default=10.0)  # Fijo: 10%
    
    # Estrategias V2: Stop-Loss y Trailing Up
    stop_loss_percent = Column(Float, default=5.0, nullable=False)  # % de pérdida máxima
    enable_stop_loss = Column(Boolean, default=True, nullable=False)  # Activado por defecto
    enable_trailing_up = Column(Boolean, default=True, nullable=False)  # Activado por defecto
    
    # CONTROL DE CONFIGURACIÓN ACTIVA - SISTEMA MULTIBOT SIMULTÁNEO
    is_active = Column(Boolean, default=False)  # Configuración activa (puede haber múltiples)
    is_configured = Column(Boolean, default=False)  # Si la configuración ha sido configurada
    is_running = Column(Boolean, default=False)  # Si el bot está ejecutándose para este par
    last_decision = Column(String(50), default='NO_DECISION')  # Última decisión del cerebro
    last_decision_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convierte el objeto a diccionario para usar en el trading engine"""
        return {
            'pair': self.pair,
            'total_capital': self.total_capital,
            'grid_levels': self.grid_levels,
            'price_range_percent': self.price_range_percent,
            'stop_loss_percent': self.stop_loss_percent,
            'enable_stop_loss': self.enable_stop_loss,
            'enable_trailing_up': self.enable_trailing_up,
            'config_type': self.config_type,
            'is_active': self.is_active,
            'is_configured': self.is_configured
        }
    
    @classmethod
    def get_default_config(cls, config_type: str) -> dict:
        """
        Obtiene la configuración por defecto para un tipo específico
        
        Args:
            config_type: 'ETH', 'BTC', 'AVAX'
            
        Returns:
            Diccionario con configuración por defecto
        """
        configs = {
            'ETH': {
                'pair': 'ETH/USDT',
                'grid_levels': 30,
                'price_range_percent': 10.0,
                'stop_loss_percent': 5.0,
                'enable_stop_loss': True,
                'enable_trailing_up': True
            },
            'BTC': {
                'pair': 'BTC/USDT',
                'grid_levels': 30,
                'price_range_percent': 7.5,  # RECETA MAESTRA BTC
                'stop_loss_percent': 5.0,
                'enable_stop_loss': True,
                'enable_trailing_up': True
            },
            'AVAX': {
                'pair': 'AVAX/USDT',
                'grid_levels': 30,
                'price_range_percent': 10.0,  # RECETA MAESTRA AVAX
                'stop_loss_percent': 5.0,
                'enable_stop_loss': True,
                'enable_trailing_up': True
            }
        }
        
        return configs.get(config_type, configs['ETH']) 