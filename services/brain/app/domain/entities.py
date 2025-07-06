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
    OPERATE = "OPERAR_GRID"
    PAUSE = "PAUSAR_GRID"
    ERROR = "ERROR"


class BotType(Enum):
    """Tipos de bots soportados."""
    GRID = "GRID"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    DCA_FUTURES = "DCA_FUTURES"


@dataclass
class MarketIndicators:
    """Indicadores de mercado calculados."""
    adx: Optional[float] = None
    volatility: Optional[float] = None
    sentiment: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    ema21: Optional[float] = None
    ema50: Optional[float] = None
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
                'timestamp': self.indicators.timestamp.isoformat() if self.indicators.timestamp else None
            },
            'thresholds': {
                'adx_threshold': self.thresholds.adx_threshold,
                'volatility_threshold': self.thresholds.volatility_threshold,
                'sentiment_threshold': self.thresholds.sentiment_threshold,
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
            adx_threshold=self.conditions['adx_threshold'],
            volatility_threshold=self.conditions['bollinger_bandwidth_threshold'],
            sentiment_threshold=self.conditions['sentiment_threshold'],
            bot_type=self.bot_type
        )


@dataclass
class BrainStatus:
    """Estado del sistema brain."""
    is_running: bool
    cycle_count: int
    last_analysis_time: Optional[datetime]
    supported_pairs: List[str]
    active_bots: List[BotType]
    total_decisions_processed: int
    successful_decisions: int
    failed_decisions: int

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el estado a diccionario."""
        return {
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'supported_pairs': self.supported_pairs,
            'active_bots': [bot.value for bot in self.active_bots],
            'total_decisions_processed': self.total_decisions_processed,
            'successful_decisions': self.successful_decisions,
            'failed_decisions': self.failed_decisions
        } 