"""
Define las interfaces (contratos) para la capa de aplicación del servicio Grid.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime

from .entities import GridConfig, GridOrder, GridBotState, GridTrade
from shared.services.logging_config import get_logger
logger = get_logger(__name__)

class GridRepository(ABC):
    """Interfaz para la persistencia de datos de grid trading."""

    @abstractmethod
    def get_active_configs(self) -> List[GridConfig]:
        """Obtiene todas las configuraciones activas de grid trading."""
        pass

    @abstractmethod
    def get_configs_with_decisions(self) -> List[Tuple[GridConfig, str, str]]:
        """
        Obtiene todas las configuraciones con sus decisiones actuales y estado anterior.
        Returns: List[Tuple[GridConfig, current_decision, previous_state]]
        """
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

    @abstractmethod
    def cancel_all_orders_for_pair(self, pair: str) -> int:
        """
        Marca como canceladas todas las órdenes activas de un par en BD.
        Retorna el número de órdenes canceladas.
        """
        pass

    # --- Nuevos métodos para escalones Grid ---
    @abstractmethod
    def get_grid_steps(self, pair: str):
        """Obtiene la lista de GridStep persistida para el par."""
        pass

    @abstractmethod
    def save_grid_steps(self, pair: str, steps) -> None:
        """Guarda la lista de GridStep para el par."""
        pass

    @abstractmethod
    def save_trade(self, trade: GridTrade) -> GridTrade:
        """Guarda un trade completado."""
        pass

    @abstractmethod
    def get_trades_by_pair(self, pair: str, limit: int = 100) -> List[GridTrade]:
        """Obtiene los trades completados para un par específico."""
        pass

    @abstractmethod
    def get_total_profit_by_pair(self, pair: str) -> Decimal:
        """Calcula el P&L total basado en trades reales para un par."""
        pass

    @abstractmethod
    def get_trades_summary_by_pair(self, pair: str) -> Dict[str, Any]:
        """Obtiene un resumen de trades para un par específico."""
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

    @abstractmethod
    def switch_to_sandbox(self) -> None:
        """Cambia el exchange a modo sandbox."""
        pass

    @abstractmethod
    def switch_to_production(self) -> None:
        """Cambia el exchange a modo producción."""
        pass

    @abstractmethod
    def cancel_all_orders(self) -> int:
        """Cancela todas las órdenes abiertas en el exchange. Retorna el número de órdenes canceladas."""
        pass

    @abstractmethod
    def cancel_all_orders_for_pair(self, pair: str) -> int:
        """Cancela todas las órdenes abiertas para un par específico. Retorna el número de órdenes canceladas."""
        pass

    @abstractmethod
    def sell_all_positions(self) -> Dict[str, Decimal]:
        """Vende todas las posiciones abiertas en el exchange. Retorna un diccionario con los montos vendidos por moneda."""
        pass

    @abstractmethod
    def get_trading_fees(self, pair: str) -> Dict[str, Decimal]:
        """Obtiene las comisiones de trading para un par."""
        pass

    @abstractmethod
    def calculate_net_amount_after_fees(self, gross_amount: Decimal, price: Decimal, side: str, pair: str) -> Decimal:
        """Calcula la cantidad neta que se recibirá después de comisiones."""
        pass

    @abstractmethod
    def get_total_balance_in_usdt(self, pair: str) -> Dict[str, Decimal]:
        """Obtiene el balance total convertido a USDT para un par específico."""
        pass

    @abstractmethod
    def get_bot_allocated_balance(self, config: GridConfig) -> Dict[str, Decimal]:
        """Obtiene el balance asignado específicamente para un bot, respetando el aislamiento de capital."""
        pass

    @abstractmethod
    def can_bot_use_capital(self, config: GridConfig, required_amount: Decimal, side: str) -> Dict[str, Any]:
        """Verifica si un bot puede usar una cantidad específica de capital sin exceder su asignación."""
        pass

    @abstractmethod
    def validate_order_after_fees(self, pair: str, side: str, amount: Decimal, price: Decimal) -> Dict[str, Any]:
        """Valida que una orden cumpla con el mínimo NOTIONAL después de las comisiones."""
        pass

    @abstractmethod
    def get_active_orders_from_exchange(self, pair: str) -> List[Dict[str, Any]]:
        """Obtiene las órdenes activas directamente del exchange para un par específico."""
        pass

    @abstractmethod
    def get_real_balances_from_exchange(self, pair: str) -> Dict[str, Any]:
        """Obtiene los balances reales directamente del exchange para un par específico."""
        pass

    @abstractmethod
    def get_filled_orders_from_exchange(self, pair: str, since_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """Obtiene órdenes completadas (fills) directamente del exchange."""
        pass

    @abstractmethod
    def get_order_status_from_exchange(self, pair: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado actual de una orden específica del exchange."""
        pass

    @abstractmethod
    def get_recent_trades_from_exchange(self, pair: str, since_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """Obtiene trades recientes ejecutados directamente del exchange."""
        pass

    @abstractmethod
    def detect_fills_by_comparison(self, pair: str, previous_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecta fills comparando órdenes activas anteriores con las actuales."""
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
    def send_info_notification(self, service_name: str, message: str) -> None:
        """Envía notificación informativa (no es un error)."""
        pass

    @abstractmethod
    def send_trade_notification(self, trade: GridTrade) -> None:
        """Envía notificación de una operación completada."""
        pass

    @abstractmethod
    def send_bot_status_notification(self, pair: str, status: str, reason: str) -> None:
        """Envía notificación de cambio de estado del bot."""
        pass

    @abstractmethod
    def send_grid_activation_notification(self, pair: str) -> None:
        """Envía notificación de activación de bot de grid."""
        pass

    @abstractmethod
    def send_grid_pause_notification(self, pair: str, cancelled_orders: int) -> None:
        """Envía notificación de pausa de bot de grid."""
        pass

    @abstractmethod
    def send_grid_summary(self, active_bots: int, total_trades: int, total_profit: float) -> None:
        """Envía resumen de actividad de grid trading."""
        pass

    @abstractmethod
    def send_decision_change_notification(self, configs_with_decisions: List[tuple]) -> None:
        """Envía notificación cuando hay cambios de decisión en la base de datos."""
        pass

    @abstractmethod
    def send_periodic_trading_summary(self, trading_stats: Dict[str, Any]) -> bool:
        """Envía resumen periódico de trading (cada 2 horas)."""
        pass

    @abstractmethod
    def send_risk_event_notification(self, event_type: str, pair: str, details: Dict[str, Any]) -> None:
        """Envía notificación específica para eventos de riesgo."""
        pass

    @abstractmethod
    def set_summary_interval(self, hours: int) -> None:
        """Configura el intervalo para resúmenes periódicos."""
        pass

    @abstractmethod
    def force_send_summary(self) -> bool:
        """Fuerza el envío inmediato del resumen periódico."""
        pass

    @abstractmethod
    def send_notification(self, message: str) -> None:
        """Envía una notificación genérica."""
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

    @abstractmethod
    def calculate_stop_loss_price(self, entry_price: Decimal, config: GridConfig, side: str) -> Optional[Decimal]:
        """Calcula el precio de stop loss."""
        pass

    @abstractmethod
    def check_stop_loss_triggered(self, current_price: Decimal, last_buy_price: Decimal, config: GridConfig) -> bool:
        """Verifica si se debe activar el stop loss."""
        pass

    @abstractmethod
    def check_trailing_up_triggered(self, current_price: Decimal, highest_sell_price: Decimal, config: GridConfig) -> bool:
        """Verifica si se debe activar el trailing up."""
        pass

    @abstractmethod
    def get_highest_sell_price(self, active_orders) -> Optional[Decimal]:
        """
        Obtiene el precio más alto de las órdenes de venta activas.
        Args:
            active_orders: Lista de órdenes activas (GridOrder o dict)
        Returns:
            Precio más alto de venta o None si no hay órdenes de venta
        """
        try:
            sell_orders = [o for o in active_orders if (getattr(o, 'side', None) == 'sell' or o.get('side') == 'sell') and (getattr(o, 'status', None) == 'open' or o.get('status') == 'open')]
            if not sell_orders:
                return None
            highest_price = max([getattr(o, 'price', None) or o.get('price') for o in sell_orders])
            return highest_price
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio más alto de venta: {e}")
            return None

    @abstractmethod
    def get_last_buy_price(self, active_orders) -> Optional[Decimal]:
        """
        Obtiene el precio de la última orden de compra ejecutada.
        Args:
            active_orders: Lista de órdenes activas (GridOrder o dict)
        Returns:
            Precio de la última compra o None si no hay compras
        """
        try:
            # Soporta tanto GridOrder como dict
            buy_orders = [o for o in active_orders if (getattr(o, 'side', None) == 'buy' or o.get('side') == 'buy') and (getattr(o, 'status', None) == 'filled' or o.get('status') == 'filled')]
            if not buy_orders:
                return None
            # Ordenar por timestamp y obtener la más reciente
            def get_time(o):
                return getattr(o, 'filled_at', None) or getattr(o, 'created_at', None) or o.get('filled_at') or o.get('created_at')
            latest_buy = max(buy_orders, key=get_time)
            return getattr(latest_buy, 'price', None) or latest_buy.get('price')
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de última compra: {e}")
            return None 