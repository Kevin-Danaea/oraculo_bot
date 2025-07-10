"""
Entidades del Dominio Brain
===========================

Define las entidades principales del sistema brain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class DecisionType(Enum):
    """Decisiones de trading posibles."""
    # Decisiones GRID
    OPERATE = "OPERAR_GRID"
    PAUSE = "PAUSAR_GRID"
    
    # Decisiones TREND
    INICIAR_COMPRA_TENDENCIA = "INICIAR_COMPRA_TENDENCIA"
    CERRAR_POSICION = "CERRAR_POSICION"
    MANTENER_ESPERA = "MANTENER_ESPERA"
    MANTENER_POSICION = "MANTENER_POSICION"
    
    # Decisiones generales
    ERROR = "ERROR"


class BotType(Enum):
    """Tipos de bots soportados."""
    GRID = "GRID"
    TREND = "TREND"
    DCA_FUTURES = "DCA_FUTURES"


class TrendPositionState(Enum):
    """Estados de posición para estrategia TREND."""
    FUERA_DEL_MERCADO = "FUERA_DEL_MERCADO"
    EN_POSICION = "EN_POSICION"


@dataclass
class MarketIndicators:
    """Indicadores de mercado calculados."""
    # Indicadores generales
    adx: Optional[float] = None
    volatility: Optional[float] = None
    sentiment: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    ema21: Optional[float] = None
    ema50: Optional[float] = None
    
    # Indicadores específicos para TREND
    sma30: Optional[float] = None
    sma150: Optional[float] = None
    sentiment_7d_avg: Optional[float] = None
    
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class TradingThresholds:
    """Umbrales para las decisiones de trading."""
    adx_threshold: float
    volatility_threshold: float
    sentiment_threshold: float
    bot_type: BotType
    
    # Umbrales específicos para TREND
    adx_trend_threshold: float = 25.0  # ADX mínimo para confirmar tendencia
    sentiment_trend_threshold: float = -0.1  # Sentimiento mínimo para entrada


@dataclass
class TrendDecision:
    """Decisión específica para estrategia TREND."""
    pair: str
    current_state: TrendPositionState
    decision: DecisionType
    reason: str
    indicators: MarketIndicators
    thresholds: TradingThresholds
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None
    
    # Información específica de tendencia
    golden_cross: bool = False
    death_cross: bool = False
    trend_strength_ok: bool = False
    sentiment_ok: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la decisión a diccionario para persistencia."""
        return {
            'pair': self.pair,
            'current_state': self.current_state.value,
            'decision': self.decision.value,
            'reason': self.reason,
            'indicators': {
                'adx': self.indicators.adx,
                'volatility': self.indicators.volatility,
                'sentiment': self.indicators.sentiment,
                'rsi': self.indicators.rsi,
                'macd': self.indicators.macd,
                'ema21': self.indicators.ema21,
                'ema50': self.indicators.ema50,
                'sma30': self.indicators.sma30,
                'sma150': self.indicators.sma150,
                'sentiment_7d_avg': self.indicators.sentiment_7d_avg,
                'timestamp': self.indicators.timestamp.isoformat() if self.indicators.timestamp else None
            },
            'thresholds': {
                'adx_threshold': self.thresholds.adx_threshold,
                'volatility_threshold': self.thresholds.volatility_threshold,
                'sentiment_threshold': self.thresholds.sentiment_threshold,
                'adx_trend_threshold': self.thresholds.adx_trend_threshold,
                'sentiment_trend_threshold': self.thresholds.sentiment_trend_threshold,
                'bot_type': self.thresholds.bot_type.value
            },
            'trend_signals': {
                'golden_cross': self.golden_cross,
                'death_cross': self.death_cross,
                'trend_strength_ok': self.trend_strength_ok,
                'sentiment_ok': self.sentiment_ok
            },
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }


@dataclass
class TradingDecision:
    """Decisión de trading para un par específico."""
    pair: str
    decision: DecisionType
    reason: str
    indicators: MarketIndicators
    thresholds: TradingThresholds
    bot_type: BotType
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la decisión a diccionario para persistencia."""
        return {
            'pair': self.pair,
            'decision': self.decision.value,
            'reason': self.reason,
            'indicators': {
                'adx': self.indicators.adx,
                'volatility': self.indicators.volatility,
                'sentiment': self.indicators.sentiment,
                'rsi': self.indicators.rsi,
                'macd': self.indicators.macd,
                'ema21': self.indicators.ema21,
                'ema50': self.indicators.ema50,
                'sma30': self.indicators.sma30,
                'sma150': self.indicators.sma150,
                'sentiment_7d_avg': self.indicators.sentiment_7d_avg,
                'timestamp': self.indicators.timestamp.isoformat() if self.indicators.timestamp else None
            },
            'thresholds': {
                'adx_threshold': self.thresholds.adx_threshold,
                'volatility_threshold': self.thresholds.volatility_threshold,
                'sentiment_threshold': self.thresholds.sentiment_threshold,
                'adx_trend_threshold': self.thresholds.adx_trend_threshold,
                'sentiment_trend_threshold': self.thresholds.sentiment_trend_threshold,
                'bot_type': self.thresholds.bot_type.value
            },
            'bot_type': self.bot_type.value,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }


@dataclass
class TradingRecipe:
    """Receta de trading para un par específico."""
    pair: str
    name: str
    conditions: Dict[str, Any]
    grid_config: Dict[str, Any]
    description: str
    bot_type: BotType = BotType.GRID

    def get_thresholds(self) -> TradingThresholds:
        """Obtiene los umbrales de la receta."""
        return TradingThresholds(
            adx_threshold=self.conditions.get('adx_threshold', 30),
            volatility_threshold=self.conditions.get('bollinger_bandwidth_threshold', 0.025),
            sentiment_threshold=self.conditions.get('sentiment_threshold', -0.20),
            adx_trend_threshold=self.conditions.get('adx_trend_threshold', 25.0),
            sentiment_trend_threshold=self.conditions.get('sentiment_trend_threshold', -0.1),
            bot_type=self.bot_type
        )


 