"""
Adaptador de infraestructura para enviar notificaciones de Hype.
"""
from datetime import datetime
from shared.services.logging_config import get_logger
from shared.services.telegram_trading import TelegramTradingService
from app.domain.entities import HypeEvent
from app.domain.interfaces import NotificationService
from typing import List

logger = get_logger(__name__)

class TelegramNotificationService(NotificationService):
    """
    Implementación de NotificationService que envía alertas a través de Telegram.
    """
    def __init__(self):
        self.telegram_service = TelegramTradingService()
        logger.info("✅ Servicio de notificación por Telegram inicializado.")

    def _format_alert(self, event: HypeEvent) -> str:
        """
        Formatea una alerta de hype para ser enviada por Telegram.
        """
        try:
            mentions_24h = event.mentions_24h
            threshold = event.threshold

            if mentions_24h >= threshold * 3:
                alert_level = "🚨 HYPE EXTREMO (VOLUMEN)"
                emoji = "🚀🚀🚀"
            elif mentions_24h >= threshold * 2:
                alert_level = "🚨 HYPE ALTO (VOLUMEN)"
                emoji = "🔥🔥"
            else:
                alert_level = "⚠️ ALERTA DE HYPE (VOLUMEN)"
                emoji = "🔥"
            
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            message = f"<b>{alert_level}</b>\n\n"
            message += f"{emoji} <b>TICKER:</b> ${event.ticker}\n"
            message += f"📈 <b>Menciones (24h):</b> {mentions_24h}\n"
            message += f"📊 <b>Umbral de alerta:</b> {threshold} menciones\n\n"
            
            if mentions_24h >= threshold * 2:
                message += "🎯 <b>TENDENCIA SOSTENIDA DETECTADA</b>\n"
                message += "💡 Actividad de menciones muy por encima de lo normal.\n\n"
            
            message += f"⏰ <i>{timestamp}</i>\n"
            message += f"🤖 <i>Hype Radar Alert System (Volume)</i>"
            
            return message
        except Exception as e:
            logger.error(f"❌ Error formateando alerta de hype por volumen: {e}")
            return f"🚨 ALERTA DE HYPE (VOLUMEN): ${event.ticker} ({event.mentions_24h} menciones)"

    def send_alert(self, event: HypeEvent) -> bool:
        """
        Envía una notificación de alerta de Hype formateada a Telegram.
        """
        try:
            logger.info(f"📢 Preparando alerta para ${event.ticker}...")
            formatted_message = self._format_alert(event)
            
            success = self.telegram_service.send_message(formatted_message)
            
            if success:
                logger.info(f"✅ Alerta para ${event.ticker} enviada a Telegram.")
            else:
                logger.error(f"❌ Falló el envío de la alerta para ${event.ticker} a Telegram.")
                
            return success
        except Exception as e:
            logger.error(f"❌ Error inesperado en send_alert para ${event.ticker}: {e}")
            return False

    def send_startup_notification(self, service_name: str, features: List[str]):
        """
        Envía una notificación de inicio de servicio formateada.
        """
        features_text = "\\n".join([f"• {feature}" for feature in features])
        message = (
            f"🚀 <b>{service_name} iniciado</b> 🚀\n\n"
            f"El servicio está operativo y monitoreando con las siguientes características:\n"
            f"{features_text}"
        )
        self.telegram_service.send_message(message)

    def send_error_notification(self, service_name: str, error: str):
        """
        Envía una notificación de error formateada.
        """
        message = (
            f"🚨 <b>Error Crítico en {service_name}</b> 🚨\n\n"
            f"Se ha producido un error que requiere atención:\n"
            f"<pre>{error}</pre>"
        )
        self.telegram_service.send_message(message)

    def send_daily_summary(self, summary_stats) -> bool:
        """Envía el resumen diario de tendencias detectadas."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            total_alerts = summary_stats.get('total_alerts_sent', 0)
            unique_tickers = summary_stats.get('unique_tickers_alerted', 0)
            top_trending = summary_stats.get('top_trending_tickers', {})
            
            message = f"<b>📊 RESUMEN DIARIO - HYPE RADAR</b>\n"
            message += f"📅 <b>Fecha:</b> {timestamp}\n\n"
            
            message += f"🚨 <b>Alertas enviadas:</b> {total_alerts}\n"
            message += f"🎯 <b>Tickers únicos alertados:</b> {unique_tickers}\n\n"
            
            if top_trending:
                message += f"🔥 <b>TOP TRENDING DEL DÍA:</b>\n"
                for i, (ticker, alerts) in enumerate(list(top_trending.items())[:5], 1):
                    message += f"{i}. ${ticker}: {alerts} alertas\n"
            else:
                message += f"😴 <b>Día tranquilo - Sin tendencias significativas</b>\n"
            
            message += f"\n⏰ <i>Resumen generado a las {datetime.now().strftime('%H:%M:%S')}</i>\n"
            message += f"🤖 <i>Hype Radar Daily Report</i>"
            
            success = self.telegram_service.send_message(message)
            
            if success:
                logger.info(f"✅ Resumen diario enviado: {total_alerts} alertas, {unique_tickers} tickers únicos")
            else:
                logger.error("❌ Error enviando resumen diario")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error enviando resumen diario: {e}")
            return False 