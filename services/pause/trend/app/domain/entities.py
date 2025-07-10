"""Domain entities for Trend Following Bot."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional


class TrendBotState(Enum):
    """Estados del bot de trend following."""
    FUERA_DEL_MERCADO = "FUERA_DEL_MERCADO"
    EN_POSICION = "EN_POSICION"


class BrainDecision(Enum):
    """Decisiones que puede tomar el cerebro."""
    INICIAR_COMPRA_TENDENCIA = "INICIAR_COMPRA_TENDENCIA"
    MANTENER_POSICION = "MANTENER_POSICION"
    MANTENER_ESPERA = "MANTENER_ESPERA"
    CERRAR_POSICION = "CERRAR_POSICION"


class ExitReason(Enum):
    """Razones de salida de posición."""
    TRAILING_STOP = "TRAILING_STOP"
    SEÑAL_CEREBRO = "SEÑAL_CEREBRO"


@dataclass
class TrendPosition:
    """Representa una posición abierta en trend following."""
    id: str
    symbol: str
    entry_price: Decimal
    entry_quantity: Decimal
    entry_time: datetime
    highest_price_since_entry: Decimal
    current_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    exit_quantity: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    fees_paid: Decimal = Decimal('0')
    
    def unrealized_pnl(self) -> Decimal:
        """Calcula el PnL no realizado."""
        if self.current_price:
            return (self.current_price - self.entry_price) * self.entry_quantity - self.fees_paid
        return Decimal('0')
    
    def realized_pnl(self) -> Decimal:
        """Calcula el PnL realizado."""
        if self.exit_price and self.exit_quantity:
            return (self.exit_price - self.entry_price) * self.exit_quantity - self.fees_paid
        return Decimal('0')
    
    def update_highest_price(self, current_price: Decimal) -> bool:
        """Actualiza el precio más alto alcanzado."""
        if current_price > self.highest_price_since_entry:
            self.highest_price_since_entry = current_price
            return True
        return False
    
    def calculate_trailing_stop(self, trailing_stop_percent: float) -> Decimal:
        """Calcula el precio de trailing stop."""
        return self.highest_price_since_entry * Decimal(str(1 - trailing_stop_percent / 100))


@dataclass
class TrendBotConfig:
    """Configuración del bot de trend following."""
    symbol: str
    capital_allocation: Decimal
    trailing_stop_percent: float = 5.0  # 5% por defecto
    sandbox_mode: bool = True
    
    def __post_init__(self):
        """Validaciones post-inicialización."""
        if self.trailing_stop_percent <= 0 or self.trailing_stop_percent > 50:
            raise ValueError("Trailing stop debe estar entre 0.1% y 50%")
        if self.capital_allocation <= 0:
            raise ValueError("Capital allocation debe ser mayor a 0")


@dataclass
class TrendBotStatus:
    """Estado interno del bot de trend following."""
    bot_id: str
    symbol: str
    state: TrendBotState
    current_position: Optional[TrendPosition] = None
    last_decision: Optional[BrainDecision] = None
    last_update: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.utcnow()


@dataclass
class BrainDirective:
    """Directiva del cerebro para el trend bot."""
    symbol: str
    decision: BrainDecision
    timestamp: datetime
    reason: Optional[str] = None
    indicators: Optional[dict] = None
    
    def is_valid(self) -> bool:
        """Verifica si la directiva es válida."""
        return bool(
            self.symbol and 
            self.decision and 
            self.timestamp and
            datetime.utcnow() - self.timestamp < timedelta(hours=24)
        )


@dataclass
class TradingResult:
    """Resultado de una operación de trading."""
    success: bool
    order_id: Optional[str] = None
    executed_price: Optional[Decimal] = None
    executed_quantity: Optional[Decimal] = None
    fees: Decimal = Decimal('0')
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class TrendBotMetrics:
    """Métricas de rendimiento del trend bot."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    best_trade: Decimal = Decimal('0')
    worst_trade: Decimal = Decimal('0')
    average_holding_time_hours: float = 0.0
    win_rate: float = 0.0
    
    def update_from_trade(self, position: TrendPosition):
        """Actualiza métricas con una posición cerrada."""
        if not position.exit_price:
            return
            
        self.total_trades += 1
        pnl = position.realized_pnl()
        self.total_pnl += pnl
        self.total_fees += position.fees_paid
        
        if pnl > 0:
            self.winning_trades += 1
            if pnl > self.best_trade:
                self.best_trade = pnl
        else:
            self.losing_trades += 1
            if pnl < self.worst_trade:
                self.worst_trade = pnl
        
        # Actualizar win rate
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        
        # Actualizar tiempo promedio de retención
        if position.exit_time and position.entry_time:
            holding_time = (position.exit_time - position.entry_time).total_seconds() / 3600
            self.average_holding_time_hours = (
                (self.average_holding_time_hours * (self.total_trades - 1) + holding_time) / 
                self.total_trades
            ) 