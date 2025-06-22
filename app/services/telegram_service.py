# Compatibilidad hacia atrás: importar desde shared
# TODO: Remover este archivo una vez completada la migración
from shared.services.telegram_service import (
    send_telegram_message,
    send_grid_trade_notification, 
    send_system_startup_notification,
    send_grid_hourly_summary
)

# Re-exportar para compatibilidad
__all__ = [
    'send_telegram_message',
    'send_grid_trade_notification', 
    'send_system_startup_notification',
    'send_grid_hourly_summary'
]
