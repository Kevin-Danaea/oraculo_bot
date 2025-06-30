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
    primary_emotion = Column(String, nullable=True)  # Emoción principal: Euforia, Optimismo, etc.
    news_category = Column(String, nullable=True)    # Categoría: Regulación, Tecnología/Adopción, etc.


class GridBotConfig(Base):
    """
    Modelo para almacenar la configuración del bot de grid trading V2.
    Incluye configuración de estrategias avanzadas: stop-loss y trailing up.
    Permite gestionar la configuración dinámicamente sin necesidad de redeploys.
    """
    __tablename__ = "grid_bot_config"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, nullable=False)  # Ej: "ETH/USDT"
    total_capital = Column(Float, nullable=False)
    grid_levels = Column(Integer, nullable=False)
    price_range_percent = Column(Float, nullable=False)
    
    # Estrategias V2: Stop-Loss y Trailing Up
    stop_loss_percent = Column(Float, default=5.0, nullable=False)  # % de pérdida máxima
    enable_stop_loss = Column(Boolean, default=True, nullable=False)  # Activado por defecto
    enable_trailing_up = Column(Boolean, default=True, nullable=False)  # Activado por defecto
    
    # Control y metadata
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
            'price_range_percent': self.price_range_percent,
            'stop_loss_percent': self.stop_loss_percent,
            'enable_stop_loss': self.enable_stop_loss,
            'enable_trailing_up': self.enable_trailing_up
        }


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


class EstrategiaStatus(Base):
    """
    Modelo para almacenar el estado de las estrategias de trading.
    Utilizado por el servicio cerebro para guardar decisiones de trading.
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
    
    # Umbrales utilizados
    umbral_adx = Column(Float, nullable=True)
    umbral_volatilidad = Column(Float, nullable=True)
    
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
            'umbral_adx': self.umbral_adx,
            'umbral_volatilidad': self.umbral_volatilidad,
            'timestamp': self.timestamp.isoformat() if self.timestamp is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        } 