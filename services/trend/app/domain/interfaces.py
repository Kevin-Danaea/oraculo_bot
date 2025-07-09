"""Domain interfaces for Trend Following Bot."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from .entities import (
    TrendSignal, TrendPosition, TrendStrategy, 
    TrendMetrics, MarketConditions, TrendDirection
)


class ITrendAnalyzer(ABC):
    """Interface para el analizador de tendencias."""
    
    @abstractmethod
    async def analyze_trend(
        self, 
        symbol: str, 
        timeframe: str,
        lookback_periods: int = 100
    ) -> MarketConditions:
        """Analiza las condiciones actuales del mercado."""
        pass
    
    @abstractmethod
    async def generate_signal(
        self,
        symbol: str,
        strategy: TrendStrategy,
        market_conditions: MarketConditions
    ) -> Optional[TrendSignal]:
        """Genera una señal de trading basada en la estrategia."""
        pass
    
    @abstractmethod
    async def calculate_indicators(
        self,
        symbol: str,
        timeframe: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula los indicadores técnicos configurados."""
        pass


class IPositionManager(ABC):
    """Interface para el gestor de posiciones."""
    
    @abstractmethod
    async def open_position(
        self,
        signal: TrendSignal,
        strategy: TrendStrategy
    ) -> TrendPosition:
        """Abre una nueva posición basada en una señal."""
        pass
    
    @abstractmethod
    async def close_position(
        self,
        position: TrendPosition,
        reason: str
    ) -> TrendPosition:
        """Cierra una posición existente."""
        pass
    
    @abstractmethod
    async def update_position(
        self,
        position: TrendPosition,
        current_price: Decimal
    ) -> TrendPosition:
        """Actualiza una posición con el precio actual."""
        pass
    
    @abstractmethod
    async def check_exit_conditions(
        self,
        position: TrendPosition,
        current_price: Decimal
    ) -> Optional[str]:
        """Verifica si se cumplen las condiciones de salida."""
        pass


class ITrendRepository(ABC):
    """Interface para el repositorio de datos del trend bot."""
    
    @abstractmethod
    async def save_signal(self, signal: TrendSignal) -> None:
        """Guarda una señal de trading."""
        pass
    
    @abstractmethod
    async def get_active_signals(self, symbol: str) -> List[TrendSignal]:
        """Obtiene las señales activas para un símbolo."""
        pass
    
    @abstractmethod
    async def save_position(self, position: TrendPosition) -> None:
        """Guarda o actualiza una posición."""
        pass
    
    @abstractmethod
    async def get_open_positions(self, symbol: Optional[str] = None) -> List[TrendPosition]:
        """Obtiene las posiciones abiertas."""
        pass
    
    @abstractmethod
    async def get_position_by_id(self, position_id: str) -> Optional[TrendPosition]:
        """Obtiene una posición por su ID."""
        pass
    
    @abstractmethod
    async def save_strategy(self, strategy: TrendStrategy) -> None:
        """Guarda o actualiza una estrategia."""
        pass
    
    @abstractmethod
    async def get_strategy(self, symbol: str) -> Optional[TrendStrategy]:
        """Obtiene la estrategia para un símbolo."""
        pass
    
    @abstractmethod
    async def get_all_strategies(self, enabled_only: bool = True) -> List[TrendStrategy]:
        """Obtiene todas las estrategias."""
        pass
    
    @abstractmethod
    async def save_metrics(self, symbol: str, metrics: TrendMetrics) -> None:
        """Guarda las métricas de rendimiento."""
        pass
    
    @abstractmethod
    async def get_metrics(self, symbol: str) -> Optional[TrendMetrics]:
        """Obtiene las métricas para un símbolo."""
        pass


class IExchangeService(ABC):
    """Interface para interactuar con el exchange."""
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal:
        """Obtiene el balance de un activo."""
        pass
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Decimal:
        """Obtiene el precio actual de un símbolo."""
        pass
    
    @abstractmethod
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal
    ) -> Dict[str, Any]:
        """Coloca una orden de mercado."""
        pass
    
    @abstractmethod
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal
    ) -> Dict[str, Any]:
        """Coloca una orden límite."""
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancela una orden."""
        pass
    
    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una orden."""
        pass
    
    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtiene datos históricos de velas."""
        pass
    
    @abstractmethod
    async def get_trading_fee(self, symbol: str) -> float:
        """Obtiene la comisión de trading para un símbolo."""
        pass


class INotificationService(ABC):
    """Interface para el servicio de notificaciones."""
    
    @abstractmethod
    async def send_signal_alert(self, signal: TrendSignal) -> None:
        """Envía una alerta de nueva señal."""
        pass
    
    @abstractmethod
    async def send_position_opened(self, position: TrendPosition) -> None:
        """Notifica que se abrió una posición."""
        pass
    
    @abstractmethod
    async def send_position_closed(
        self,
        position: TrendPosition,
        reason: str
    ) -> None:
        """Notifica que se cerró una posición."""
        pass
    
    @abstractmethod
    async def send_error_alert(self, error: str, details: Optional[Dict] = None) -> None:
        """Envía una alerta de error."""
        pass
    
    @abstractmethod
    async def send_daily_summary(self, metrics: TrendMetrics, positions: List[TrendPosition]) -> None:
        """Envía un resumen diario de rendimiento."""
        pass


class IRiskManager(ABC):
    """Interface para el gestor de riesgo."""
    
    @abstractmethod
    async def validate_signal(
        self,
        signal: TrendSignal,
        strategy: TrendStrategy,
        current_balance: Decimal
    ) -> bool:
        """Valida si una señal cumple con los criterios de riesgo."""
        pass
    
    @abstractmethod
    async def calculate_position_size(
        self,
        signal: TrendSignal,
        strategy: TrendStrategy,
        current_balance: Decimal
    ) -> Decimal:
        """Calcula el tamaño óptimo de la posición."""
        pass
    
    @abstractmethod
    async def check_exposure(
        self,
        open_positions: List[TrendPosition],
        strategy: TrendStrategy
    ) -> bool:
        """Verifica si la exposición actual está dentro de límites."""
        pass
    
    @abstractmethod
    async def calculate_stop_loss(
        self,
        entry_price: Decimal,
        direction: TrendDirection,
        strategy: TrendStrategy,
        atr_value: Optional[Decimal] = None
    ) -> Decimal:
        """Calcula el nivel de stop loss."""
        pass
    
    @abstractmethod
    async def calculate_take_profit(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        direction: TrendDirection,
        strategy: TrendStrategy
    ) -> Decimal:
        """Calcula el nivel de take profit."""
        pass 