"""Domain entities for Trend Following Bot."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any


class TrendDirection(Enum):
    """Dirección de la tendencia detectada."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PositionStatus(Enum):
    """Estado de una posición de trading."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class SignalStrength(Enum):
    """Fuerza de la señal de tendencia."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


@dataclass
class TrendSignal:
    """Representa una señal de tendencia detectada."""
    id: str
    symbol: str
    direction: TrendDirection
    strength: SignalStrength
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    confidence: float  # 0.0 a 1.0
    indicators: Dict[str, Any]  # Valores de indicadores técnicos
    timestamp: datetime
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Verifica si la señal sigue siendo válida."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def risk_reward_ratio(self) -> float:
        """Calcula el ratio riesgo/recompensa."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return float(reward / risk) if risk > 0 else 0.0


@dataclass
class TrendPosition:
    """Representa una posición abierta siguiendo una tendencia."""
    id: str
    symbol: str
    signal_id: str
    status: PositionStatus
    side: str  # BUY o SELL
    entry_price: Decimal
    entry_quantity: Decimal
    entry_time: datetime
    current_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    exit_quantity: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    stop_loss: Decimal = Decimal('0')
    take_profit: Decimal = Decimal('0')
    trailing_stop_distance: Optional[Decimal] = None
    max_price_seen: Optional[Decimal] = None  # Para trailing stop
    fees_paid: Decimal = Decimal('0')
    
    def unrealized_pnl(self) -> Decimal:
        """Calcula el PnL no realizado."""
        if self.current_price and self.status == PositionStatus.OPEN:
            if self.side == "BUY":
                return (self.current_price - self.entry_price) * self.entry_quantity - self.fees_paid
            else:  # SELL
                return (self.entry_price - self.current_price) * self.entry_quantity - self.fees_paid
        return Decimal('0')
    
    def realized_pnl(self) -> Decimal:
        """Calcula el PnL realizado."""
        if self.exit_price and self.exit_quantity and self.status == PositionStatus.CLOSED:
            if self.side == "BUY":
                return (self.exit_price - self.entry_price) * self.exit_quantity - self.fees_paid
            else:  # SELL
                return (self.entry_price - self.exit_price) * self.exit_quantity - self.fees_paid
        return Decimal('0')
    
    def update_trailing_stop(self, current_price: Decimal) -> Optional[Decimal]:
        """Actualiza el trailing stop basado en el precio actual."""
        if not self.trailing_stop_distance or self.side != "BUY":
            return None
            
        # Actualizar el precio máximo visto
        if not self.max_price_seen or current_price > self.max_price_seen:
            self.max_price_seen = current_price
            
        # Calcular nuevo stop loss
        new_stop = self.max_price_seen - self.trailing_stop_distance
        
        # Solo actualizar si es mayor que el stop loss actual
        if new_stop > self.stop_loss:
            self.stop_loss = new_stop
            return new_stop
            
        return None


@dataclass
class TrendStrategy:
    """Configuración de la estrategia de trend following."""
    name: str
    symbol: str
    enabled: bool
    capital_allocation: Decimal
    max_position_size: Decimal
    min_position_size: Decimal
    
    # Gestión de riesgo
    stop_loss_percentage: float  # % desde el precio de entrada
    take_profit_percentage: float  # % desde el precio de entrada
    trailing_stop_percentage: Optional[float] = None  # % desde el máximo
    max_positions: int = 1  # Máximo de posiciones abiertas simultáneas
    
    # Indicadores técnicos
    indicators_config: Optional[Dict[str, Any]] = None
    
    # Filtros de entrada
    min_signal_strength: SignalStrength = SignalStrength.MODERATE
    min_confidence: float = 0.7
    
    # Timeframes
    analysis_timeframe: str = "4h"  # Timeframe principal
    confirmation_timeframe: Optional[str] = "1h"  # Timeframe de confirmación
    
    def __post_init__(self):
        if self.indicators_config is None:
            self.indicators_config = {
                "ema_fast": 20,
                "ema_slow": 50,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_period": 14,
                "volume_ma": 20
            }


@dataclass
class TrendMetrics:
    """Métricas de rendimiento del bot de trend following."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    sharpe_ratio: Optional[float] = None
    win_rate: float = 0.0
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')
    profit_factor: float = 0.0
    best_trade: Decimal = Decimal('0')
    worst_trade: Decimal = Decimal('0')
    average_holding_time: Optional[float] = None  # En horas
    current_streak: int = 0  # Positivo para ganadoras, negativo para perdedoras
    
    def update_from_position(self, position: TrendPosition):
        """Actualiza las métricas con una posición cerrada."""
        if position.status != PositionStatus.CLOSED:
            return
            
        pnl = position.realized_pnl()
        self.total_trades += 1
        self.total_pnl += pnl
        self.total_fees += position.fees_paid
        
        if pnl > 0:
            self.winning_trades += 1
            self.average_win = (
                (self.average_win * (self.winning_trades - 1) + pnl) / 
                self.winning_trades
            )
            self.current_streak = max(1, self.current_streak + 1)
            if pnl > self.best_trade:
                self.best_trade = pnl
        else:
            self.losing_trades += 1
            self.average_loss = (
                (self.average_loss * (self.losing_trades - 1) + abs(pnl)) / 
                self.losing_trades
            )
            self.current_streak = min(-1, self.current_streak - 1)
            if pnl < self.worst_trade:
                self.worst_trade = pnl
        
        # Actualizar win rate
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        
        # Actualizar profit factor
        if self.average_loss > 0:
            self.profit_factor = float(
                (self.average_win * self.winning_trades) / 
                (self.average_loss * self.losing_trades)
            )


@dataclass
class MarketConditions:
    """Condiciones actuales del mercado."""
    symbol: str
    timestamp: datetime
    trend: TrendDirection
    volatility: float  # ATR normalizado
    volume_ratio: float  # Volumen actual vs promedio
    market_phase: str  # "accumulation", "markup", "distribution", "markdown"
    strength_index: float  # 0-100
    support_levels: List[Decimal]
    resistance_levels: List[Decimal] 