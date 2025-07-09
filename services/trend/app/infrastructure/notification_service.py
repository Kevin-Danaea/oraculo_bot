"""Notification service implementation for Telegram."""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from shared.services.telegram_base import TelegramBaseService
from ..domain.entities import TrendSignal, TrendPosition, TrendMetrics
from ..domain.interfaces import INotificationService
from ..config import get_config

logger = logging.getLogger(__name__)


class NotificationService(INotificationService):
    """Implementación del servicio de notificaciones usando Telegram."""
    
    def __init__(self):
        self.config = get_config()
        self.telegram = TelegramBaseService()
        
    async def send_signal_alert(self, signal: TrendSignal) -> None:
        """Envía una alerta de nueva señal."""
        try:
            emoji = "🔥" if signal.direction.value == "BULLISH" else "🔻"
            strength_emoji = {
                "STRONG": "💪",
                "MODERATE": "👌", 
                "WEAK": "🤏"
            }
            
            message = (
                f"{emoji} **NUEVA SEÑAL TREND** {emoji}\n\n"
                f"🪙 **Par:** {signal.symbol}\n"
                f"📈 **Dirección:** {signal.direction.value}\n"
                f"{strength_emoji.get(signal.strength.value, '📊')} **Fuerza:** {signal.strength.value}\n"
                f"💰 **Precio Entrada:** ${signal.entry_price:,.2f}\n"
                f"🛑 **Stop Loss:** ${signal.stop_loss:,.2f}\n"
                f"🎯 **Take Profit:** ${signal.take_profit:,.2f}\n"
                f"🎲 **Confianza:** {signal.confidence:.1%}\n"
                f"⚖️ **R/R Ratio:** {signal.risk_reward_ratio():.2f}\n\n"
                f"⏰ **Tiempo:** {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            self.telegram.send_message(message, self.config.telegram_chat_id)
            logger.info(f"Alerta de señal enviada para {signal.symbol}")
            
        except Exception as e:
            logger.error(f"Error enviando alerta de señal: {str(e)}")
    
    async def send_position_opened(self, position: TrendPosition) -> None:
        """Notifica que se abrió una posición."""
        try:
            emoji = "🚀" if position.side == "BUY" else "📉"
            
            message = (
                f"{emoji} **POSICIÓN ABIERTA** {emoji}\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"📊 **Tipo:** {position.side}\n"
                f"💰 **Precio:** ${position.entry_price:,.2f}\n"
                f"📦 **Cantidad:** {position.entry_quantity:.6f}\n"
                f"💵 **Valor:** ${float(position.entry_price * position.entry_quantity):,.2f}\n"
                f"🛑 **Stop Loss:** ${position.stop_loss:,.2f}\n"
                f"🎯 **Take Profit:** ${position.take_profit:,.2f}\n\n"
                f"⏰ **Tiempo:** {position.entry_time.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            self.telegram.send_message(message, self.config.telegram_chat_id)
            logger.info(f"Notificación de posición abierta enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"Error enviando notificación de posición abierta: {str(e)}")
    
    async def send_position_closed(
        self,
        position: TrendPosition,
        reason: str
    ) -> None:
        """Notifica que se cerró una posición."""
        try:
            pnl = position.realized_pnl()
            pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
            
            emoji = "✅" if pnl > 0 else "❌"
            pnl_emoji = "💰" if pnl > 0 else "💸"
            
            message = (
                f"{emoji} **POSICIÓN CERRADA** {emoji}\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"📊 **Tipo:** {position.side}\n"
                f"💰 **Precio Entrada:** ${position.entry_price:,.2f}\n"
                f"🏁 **Precio Salida:** ${position.exit_price:,.2f}\n"
                f"📦 **Cantidad:** {position.exit_quantity:.6f}\n"
                f"{pnl_emoji} **PnL:** ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                f"💸 **Comisiones:** ${position.fees_paid:,.2f}\n"
                f"📝 **Razón:** {reason}\n\n"
                f"⏰ **Tiempo:** {position.exit_time.strftime('%Y-%m-%d %H:%M UTC') if position.exit_time else 'N/A'}"
            )
            
            await self.telegram.send_message(message)
            logger.info(f"Notificación de posición cerrada enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"Error enviando notificación de posición cerrada: {str(e)}")
    
    async def send_error_alert(self, error: str, details: Optional[Dict] = None) -> None:
        """Envía una alerta de error."""
        try:
            message = f"⚠️ **ERROR TREND BOT** ⚠️\n\n{error}"
            
            if details:
                message += "\n\n📋 **Detalles:**\n"
                for key, value in details.items():
                    message += f"• {key}: {value}\n"
            
            await self.telegram.send_message(message)
            logger.info("Alerta de error enviada")
            
        except Exception as e:
            logger.error(f"Error enviando alerta de error: {str(e)}")
    
    async def send_daily_summary(
        self, 
        metrics: TrendMetrics, 
        positions: List[TrendPosition]
    ) -> None:
        """Envía un resumen diario de rendimiento."""
        try:
            # Posiciones abiertas
            open_positions = [p for p in positions if p.status.value == "OPEN"]
            
            # PnL no realizado total
            unrealized_pnl = sum(pos.unrealized_pnl() for pos in open_positions)
            
            message = (
                f"📊 **RESUMEN DIARIO TREND BOT** 📊\n\n"
                f"📈 **Rendimiento General:**\n"
                f"• Total Trades: {metrics.total_trades}\n"
                f"• Ganadores: {metrics.winning_trades} ({metrics.win_rate:.1%})\n"
                f"• Perdedores: {metrics.losing_trades}\n"
                f"• PnL Total: ${metrics.total_pnl:,.2f}\n"
                f"• Comisiones: ${metrics.total_fees:,.2f}\n"
                f"• PnL Neto: ${metrics.total_pnl - metrics.total_fees:,.2f}\n\n"
                f"🎯 **Métricas de Trading:**\n"
                f"• Mejor Trade: ${metrics.best_trade:,.2f}\n"
                f"• Peor Trade: ${metrics.worst_trade:,.2f}\n"
                f"• Ganancia Promedio: ${metrics.average_win:,.2f}\n"
                f"• Pérdida Promedio: ${metrics.average_loss:,.2f}\n"
                f"• Profit Factor: {metrics.profit_factor:.2f}\n"
                f"• Racha Actual: {metrics.current_streak:+d}\n\n"
                f"📋 **Posiciones Actuales:**\n"
                f"• Abiertas: {len(open_positions)}\n"
                f"• PnL No Realizado: ${unrealized_pnl:,.2f}\n\n"
            )
            
            if open_positions:
                message += "🔄 **Posiciones Abiertas:**\n"
                for pos in open_positions[:5]:  # Máximo 5 posiciones
                    pnl = pos.unrealized_pnl()
                    pnl_percent = float(pnl / (pos.entry_price * pos.entry_quantity) * 100)
                    emoji = "📈" if pnl > 0 else "📉"
                    
                    message += (
                        f"{emoji} {pos.symbol}: ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                    )
                
                if len(open_positions) > 5:
                    message += f"... y {len(open_positions) - 5} más\n"
            
            await self.telegram.send_message(message)
            logger.info("Resumen diario enviado")
            
        except Exception as e:
            logger.error(f"Error enviando resumen diario: {str(e)}") 