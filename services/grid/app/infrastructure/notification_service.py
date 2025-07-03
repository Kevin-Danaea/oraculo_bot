"""
Servicio de notificaciones para Grid Trading.
"""
from typing import List
from datetime import datetime

from app.domain.interfaces import NotificationService
from app.domain.entities import GridTrade
from shared.services.telegram_trading import TelegramTradingService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class TelegramGridNotificationService(NotificationService):
    """Implementación de notificaciones usando Telegram."""

    def __init__(self):
        """Inicializa el servicio de notificaciones."""
        self.telegram_service = TelegramTradingService()
        logger.info("✅ TelegramGridNotificationService inicializado.")

    def send_startup_notification(self, service_name: str, features: List[str]) -> None:
        """Envía notificación de inicio del servicio."""
        try:
            features_text = "\n".join([f"• {feature}" for feature in features])
            message = (
                f"🚀 <b>{service_name} iniciado</b> 🚀\n\n"
                f"El servicio está operativo con las siguientes características:\n"
                f"{features_text}\n\n"
                f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de inicio enviada para {service_name}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {e}")

    def send_error_notification(self, service_name: str, error: str) -> None:
        """Envía notificación de error."""
        try:
            message = (
                f"🚨 <b>Error en {service_name}</b> 🚨\n\n"
                f"Se ha producido un error:\n"
                f"<pre>{error}</pre>\n\n"
                f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de error enviada para {service_name}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}")

    def send_trade_notification(self, trade: GridTrade) -> None:
        """Envía notificación de una operación completada."""
        try:
            profit_emoji = "💰" if trade.profit > 0 else "📉"
            
            message = (
                f"{profit_emoji} <b>TRADE COMPLETADO - GRID</b>\n\n"
                f"💱 <b>Par:</b> {trade.pair}\n"
                f"💵 <b>Ganancia:</b> ${trade.profit:.4f} USDT ({trade.profit_percent:.2f}%)\n"
                f"📊 <b>Cantidad:</b> {trade.amount}\n"
                f"📈 <b>Compra:</b> ${trade.buy_price}\n"
                f"📉 <b>Venta:</b> ${trade.sell_price}\n\n"
                f"⏰ <i>{trade.executed_at.strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de trade enviada: {trade.pair} +${trade.profit:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de trade: {e}")

    def send_bot_status_notification(self, pair: str, status: str, reason: str) -> None:
        """Envía notificación de cambio de estado del bot."""
        try:
            status_emoji = "🟢" if status == "started" else "🔴"
            status_text = "INICIADO" if status == "started" else "DETENIDO"
            
            message = (
                f"{status_emoji} <b>BOT GRID {status_text}</b>\n\n"
                f"💱 <b>Par:</b> {pair}\n"
                f"📋 <b>Estado:</b> {status_text}\n"
                f"💭 <b>Razón:</b> {reason}\n\n"
                f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de estado enviada: {pair} -> {status}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de estado: {e}")

    def send_grid_summary(self, active_bots: int, total_trades: int, total_profit: float) -> None:
        """Envía resumen del estado general de los bots."""
        try:
            message = (
                f"📊 <b>RESUMEN GRID TRADING</b>\n\n"
                f"🤖 <b>Bots activos:</b> {active_bots}\n"
                f"💼 <b>Trades totales:</b> {total_trades}\n"
                f"💰 <b>Ganancia total:</b> ${total_profit:.2f} USDT\n\n"
                f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            )
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Resumen de grid enviado: {active_bots} bots, ${total_profit:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando resumen de grid: {e}") 