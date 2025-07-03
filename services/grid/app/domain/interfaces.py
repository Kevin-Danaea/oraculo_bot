"""
Define las interfaces (contratos) para la capa de aplicación del servicio Grid.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from .entities import GridConfig, GridOrder, GridBotState, GridTrade

class GridRepository(ABC):
    """Interfaz para la persistencia de datos de grid trading."""

    @abstractmethod
    def get_active_configs(self) -> List[GridConfig]:
        """Obtiene todas las configuraciones activas de grid trading."""
        pass

    @abstractmethod
    def get_config_by_pair(self, pair: str) -> Optional[GridConfig]:
        """Obtiene la configuración para un par específico."""
        pass

    @abstractmethod
    def update_config_status(self, config_id: int, is_running: bool, last_decision: str) -> None:
        """Actualiza el estado de una configuración."""
        pass

    @abstractmethod
    def get_bot_state(self, pair: str) -> Optional[GridBotState]:
        """Obtiene el estado completo de un bot para un par."""
        pass

    @abstractmethod
    def save_bot_state(self, bot_state: GridBotState) -> None:
        """Guarda el estado completo de un bot."""
        pass

    @abstractmethod
    def get_active_orders(self, pair: str) -> List[GridOrder]:
        """Obtiene las órdenes activas para un par."""
        pass

    @abstractmethod
    def save_order(self, order: GridOrder) -> GridOrder:
        """Guarda una orden de grid trading."""
        pass

    @abstractmethod
    def update_order_status(self, order_id: str, status: str, filled_at: Optional[datetime] = None) -> None:
        """Actualiza el estado de una orden."""
        pass

class ExchangeService(ABC):
    """Interfaz para interactuar con el exchange."""

    @abstractmethod
    def get_current_price(self, pair: str) -> Decimal:
        """Obtiene el precio actual de un par."""
        pass

    @abstractmethod
    def get_balance(self, currency: str) -> Decimal:
        """Obtiene el balance de una moneda."""
        pass

    @abstractmethod
    def create_order(self, pair: str, side: str, amount: Decimal, price: Decimal, order_type: str = 'limit') -> GridOrder:
        """Crea una orden en el exchange."""
        pass

    @abstractmethod
    def cancel_order(self, pair: str, order_id: str) -> bool:
        """Cancela una orden en el exchange."""
        pass

    @abstractmethod
    def get_order_status(self, pair: str, order_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una orden en el exchange."""
        pass

    @abstractmethod
    def get_minimum_order_value(self, pair: str) -> Decimal:
        """Obtiene el valor mínimo de orden para un par."""
        pass
    
    @abstractmethod
    def get_trading_mode(self) -> str:
        """Obtiene el modo de trading actual."""
        pass

class NotificationService(ABC):
    """Interfaz para servicios de notificación."""

    @abstractmethod
    def send_startup_notification(self, service_name: str, features: List[str]) -> None:
        """Envía notificación de inicio del servicio."""
        pass

    @abstractmethod
    def send_error_notification(self, service_name: str, error: str) -> None:
        """Envía notificación de error."""
        pass

    @abstractmethod
    def send_trade_notification(self, trade: GridTrade) -> None:
        """Envía notificación de una operación completada."""
        pass

    @abstractmethod
    def send_bot_status_notification(self, pair: str, status: str, reason: str) -> None:
        """Envía notificación de cambio de estado del bot."""
        pass

class GridCalculator(ABC):
    """Interfaz para cálculos de grid trading."""

    @abstractmethod
    def calculate_grid_levels(self, current_price: Decimal, config: GridConfig) -> List[Decimal]:
        """Calcula los niveles de precio para la grilla."""
        pass

    @abstractmethod
    def calculate_order_amount(self, total_capital: float, grid_levels: int, current_price: Decimal) -> Decimal:
        """Calcula la cantidad por orden basada en el capital total."""
        pass

    @abstractmethod
    def should_create_buy_order(self, current_price: Decimal, existing_orders: List[GridOrder], grid_levels: List[Decimal]) -> Optional[Decimal]:
        """Determina si se debe crear una orden de compra y a qué precio."""
        pass

    @abstractmethod
    def should_create_sell_order(self, current_price: Decimal, existing_orders: List[GridOrder], grid_levels: List[Decimal]) -> Optional[Decimal]:
        """Determina si se debe crear una orden de venta y a qué precio."""
        pass 