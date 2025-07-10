"""Domain interfaces for Trend Following Bot."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, List

from .entities import (
    TrendBotStatus, TrendPosition, BrainDirective, 
    TradingResult, TrendBotConfig, TrendBotMetrics
)


class ITrendBotRepository(ABC):
    """Interface para el repositorio del trend bot."""
    
    @abstractmethod
    async def save_bot_status(self, status: TrendBotStatus) -> None:
        """Guarda el estado del bot."""
        pass
    
    @abstractmethod
    async def get_bot_status(self, bot_id: str) -> Optional[TrendBotStatus]:
        """Obtiene el estado del bot."""
        pass
    
    @abstractmethod
    async def save_position(self, position: TrendPosition) -> None:
        """Guarda una posición."""
        pass
    
    @abstractmethod
    async def get_current_position(self, bot_id: str) -> Optional[TrendPosition]:
        """Obtiene la posición actual del bot."""
        pass
    
    @abstractmethod
    async def save_metrics(self, bot_id: str, metrics: TrendBotMetrics) -> None:
        """Guarda las métricas del bot."""
        pass
    
    @abstractmethod
    async def get_metrics(self, bot_id: str) -> Optional[TrendBotMetrics]:
        """Obtiene las métricas del bot."""
        pass


class IBrainDirectiveRepository(ABC):
    """Interface para obtener directivas del cerebro."""
    
    @abstractmethod
    async def get_latest_directive(self, symbol: str) -> Optional[BrainDirective]:
        """Obtiene la última directiva del cerebro para un símbolo."""
        pass


class IExchangeService(ABC):
    """Interface para interactuar con el exchange."""
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Decimal:
        """Obtiene el precio actual de un símbolo."""
        pass
    
    @abstractmethod
    def get_balance(self, asset: str) -> Decimal:
        """Obtiene el balance de un activo."""
        pass
    
    @abstractmethod
    def place_market_buy_order(
        self, 
        symbol: str, 
        quantity: Decimal
    ) -> TradingResult:
        """Coloca una orden de compra a mercado."""
        pass
    
    @abstractmethod
    def place_market_sell_order(
        self, 
        symbol: str, 
        quantity: Decimal
    ) -> TradingResult:
        """Coloca una orden de venta a mercado."""
        pass


class INotificationService(ABC):
    """Interface para el servicio de notificaciones."""
    
    @abstractmethod
    async def send_position_opened(
        self, 
        position: TrendPosition, 
        config: TrendBotConfig
    ) -> None:
        """Notifica que se abrió una posición."""
        pass
    
    @abstractmethod
    async def send_position_closed(
        self, 
        position: TrendPosition, 
        exit_reason: str
    ) -> None:
        """Notifica que se cerró una posición."""
        pass
    
    @abstractmethod
    async def send_trailing_stop_exit(
        self, 
        position: TrendPosition, 
        current_price: Decimal,
        trailing_stop_price: Decimal
    ) -> None:
        """Notifica salida por trailing stop."""
        pass
    
    @abstractmethod
    async def send_brain_signal_exit(
        self, 
        position: TrendPosition, 
        directive: BrainDirective
    ) -> None:
        """Notifica salida por señal del cerebro."""
        pass
    
    @abstractmethod
    async def send_error_notification(
        self, 
        error: str, 
        details: Optional[dict] = None
    ) -> None:
        """Envía notificación de error."""
        pass
    
    @abstractmethod
    async def send_startup_notification(
        self, 
        config: TrendBotConfig
    ) -> None:
        """Envía notificación de inicio del bot."""
        pass


class ITrendBotStateManager(ABC):
    """Interface para gestionar el estado del bot."""
    
    @abstractmethod
    async def initialize_state(self, bot_id: str, config: TrendBotConfig) -> TrendBotStatus:
        """Inicializa el estado del bot."""
        pass
    
    @abstractmethod
    async def update_state(self, status: TrendBotStatus) -> None:
        """Actualiza el estado del bot."""
        pass
    
    @abstractmethod
    async def get_state(self, bot_id: str) -> Optional[TrendBotStatus]:
        """Obtiene el estado actual del bot."""
        pass
    
    @abstractmethod
    async def save_state(self, status: TrendBotStatus) -> None:
        """Guarda el estado del bot."""
        pass 