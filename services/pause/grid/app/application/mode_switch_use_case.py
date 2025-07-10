"""
Caso de uso para cambiar modo sandbox/producción y limpiar estado actual del Grid Trading.
"""
from typing import Dict, Any
from decimal import Decimal
from app.domain.interfaces import GridRepository, ExchangeService, NotificationService
from app.domain.entities import GridOrder

class ModeSwitchUseCase:
    """
    Caso de uso para manejar el cambio de modo y limpieza de órdenes y posiciones.
    """
    def __init__(
        self,
        grid_repository: GridRepository,
        exchange_service: ExchangeService,
        notification_service: NotificationService
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service

    def switch_to_sandbox(self) -> Dict[str, Any]:
        """
        Cambia a modo sandbox, cancela órdenes y liquida posiciones actuales.
        """
        self.exchange_service.switch_to_sandbox()
        return self._cleanup()

    def switch_to_production(self) -> Dict[str, Any]:
        """
        Cambia a modo producción, cancela órdenes y liquida posiciones actuales.
        """
        self.exchange_service.switch_to_production()
        return self._cleanup()

    def _cleanup(self) -> Dict[str, Any]:
        """
        Cancela todas las órdenes abiertas y liquida posiciones de cada bot.
        """
        # Usar métodos genéricos para limpiar exchange
        configs = self.grid_repository.get_active_configs()
        # Cancelar en el exchange y obtener número de órdenes canceladas
        exchange_cancelled = self.exchange_service.cancel_all_orders()
        # Liquidar todas las posiciones y obtener detalles de montos vendidos
        sold_positions = self.exchange_service.sell_all_positions()
        # Reflejar cancelaciones en la BD por cada configuración activa
        db_cancelled = 0
        for config in configs:
            db_cancelled += self.grid_repository.cancel_all_orders_for_pair(config.pair)

        # Notificar cambio de estado y resultados
        self.notification_service.send_bot_status_notification(
            pair='ALL',
            status='mode_switch',
            reason=(
                f'Exchange: canceladas {exchange_cancelled} órdenes, ' +
                f'BD: canceladas {db_cancelled} órdenes, ' +
                f'posiciones liquidadas: {list(sold_positions.keys())}'
            )
        )

        return {
            'exchange_cancelled_orders': exchange_cancelled,
            'db_cancelled_orders': db_cancelled,
            'sold_positions': sold_positions
        } 