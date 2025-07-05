"""
Entidades del dominio para el servicio Grid.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

@dataclass
class GridConfig:
    """Configuración de un bot de grid trading."""
    id: Optional[int]
    telegram_chat_id: str
    config_type: str  # 'BTC', 'ETH', 'AVAX'
    pair: str
    total_capital: float
    grid_levels: int
    price_range_percent: float
    stop_loss_percent: float
    enable_stop_loss: bool
    enable_trailing_up: bool
    is_active: bool
    is_configured: bool
    is_running: bool
    last_decision: str
    last_decision_timestamp: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

@dataclass 
class GridOrder:
    """Representa una orden de grid trading."""
    id: Optional[str]
    exchange_order_id: Optional[str]
    pair: str
    side: str  # 'buy' o 'sell'
    amount: Decimal
    price: Decimal
    status: str  # 'open', 'filled', 'cancelled'
    order_type: str  # 'grid_buy', 'grid_sell', 'stop_loss'
    grid_level: Optional[int]
    created_at: Optional[datetime]
    filled_at: Optional[datetime]
    
@dataclass
class GridBotState:
    """Estado actual de un bot de grid trading."""
    pair: str
    config: GridConfig
    active_orders: List[GridOrder]
    total_profit: Decimal
    total_trades: int
    current_price: Optional[Decimal]
    grid_upper_bound: Optional[Decimal]
    grid_lower_bound: Optional[Decimal]
    is_active: bool
    last_update: Optional[datetime]

    # Capital comprometido (USDT) y monto base comprometido (asset del par)
    capital_committed_usdt: Decimal = Decimal('0')
    base_committed_amount: Decimal = Decimal('0')

@dataclass
class TradingDecision:
    """Decisión de trading basada en el monitoreo."""
    pair: str
    action: str  # 'start_bot', 'stop_bot', 'continue', 'no_action'
    reason: str
    config: Optional[GridConfig]
    timestamp: datetime

@dataclass
class GridTrade:
    """Representa una operación completada de grid trading."""
    pair: str
    buy_order_id: str
    sell_order_id: str
    buy_price: Decimal
    sell_price: Decimal
    amount: Decimal
    profit: Decimal
    profit_percent: Decimal
    executed_at: datetime

@dataclass
class GridStep:
    """Representa un escalón del grid con un nivel inferior y otro superior.
    En cada momento sólo hay una orden activa (buy o sell) asociada al escalón.
    """
    pair: str
    level_index: int  # índice del escalón 0..(grid_levels-1)
    buy_level_price: Decimal
    sell_level_price: Decimal
    active_order_id: Optional[str]
    active_side: Optional[str]  # 'buy' o 'sell'
    last_filled_side: Optional[str] = None 