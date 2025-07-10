"""Notification service implementation for Telegram."""

import logging
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime

from shared.services.telegram_base import TelegramBaseService
from ..domain.entities import TrendPosition, TrendBotConfig, BrainDirective
from ..domain.interfaces import INotificationService
from ..config import get_config

logger = logging.getLogger(__name__)


class NotificationService(INotificationService):
    """Implementación del servicio de notificaciones usando Telegram."""
    
    def __init__(self):
        self.config = get_config()
        self.telegram = TelegramBaseService()
        
    async def send_position_opened(
        self, 
        position: TrendPosition, 
        config: TrendBotConfig
    ) -> None:
        """Notifica que se abrió una posición."""
        try:
            message = (
                f"🚀 **POSICIÓN ABIERTA - TREND BOT** 🚀\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"💰 **Precio Entrada:** ${position.entry_price:,.2f}\n"
                f"📦 **Cantidad:** {position.entry_quantity:.6f}\n"
                f"💵 **Valor:** ${float(position.entry_price * position.entry_quantity):,.2f}\n"
                f"🛑 **Trailing Stop:** {config.trailing_stop_percent}%\n"
                f"💸 **Comisiones:** ${position.fees_paid:,.2f}\n\n"
                f"⏰ **Tiempo:** {position.entry_time.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"📊 **Configuración:**\n"
                f"• Capital: ${config.capital_allocation:,.2f}\n"
                f"• Modo: {'Testnet' if config.sandbox_mode else 'Real'}"
            )
            
            self.telegram.send_message(message)
            logger.info(f"✅ Notificación de posición abierta enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de posición abierta: {str(e)}")
    
    async def send_position_closed(
        self, 
        position: TrendPosition, 
        exit_reason: str
    ) -> None:
        """Notifica que se cerró una posición."""
        try:
            pnl = position.realized_pnl()
            pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
            
            emoji = "✅" if pnl > 0 else "❌"
            pnl_emoji = "💰" if pnl > 0 else "💸"
            
            message = (
                f"{emoji} **POSICIÓN CERRADA - TREND BOT** {emoji}\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"💰 **Precio Entrada:** ${position.entry_price:,.2f}\n"
                f"🏁 **Precio Salida:** ${position.exit_price:,.2f}\n"
                f"📦 **Cantidad:** {position.exit_quantity:.6f}\n"
                f"{pnl_emoji} **PnL:** ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                f"💸 **Comisiones:** ${position.fees_paid:,.2f}\n"
                f"📝 **Razón:** {exit_reason}\n\n"
                f"⏰ **Tiempo:** {position.exit_time.strftime('%Y-%m-%d %H:%M UTC') if position.exit_time else 'N/A'}"
            )
            
            self.telegram.send_message(message)
            logger.info(f"✅ Notificación de posición cerrada enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de posición cerrada: {str(e)}")
    
    async def send_trailing_stop_exit(
        self, 
        position: TrendPosition, 
        current_price: Decimal,
        trailing_stop_price: Decimal
    ) -> None:
        """Notifica salida por trailing stop."""
        try:
            pnl = position.realized_pnl()
            pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
            
            emoji = "✅" if pnl > 0 else "❌"
            
            message = (
                f"🛑 **SALIDA POR TRAILING STOP** 🛑\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"💰 **Precio Entrada:** ${position.entry_price:,.2f}\n"
                f"📈 **Precio Máximo:** ${position.highest_price_since_entry:,.2f}\n"
                f"📉 **Precio Actual:** ${current_price:,.2f}\n"
                f"🛑 **Trailing Stop:** ${trailing_stop_price:,.2f}\n"
                f"🏁 **Precio Salida:** ${position.exit_price:,.2f}\n"
                f"📦 **Cantidad:** {position.exit_quantity:.6f}\n"
                f"{emoji} **PnL:** ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                f"💸 **Comisiones:** ${position.fees_paid:,.2f}\n\n"
                f"⏰ **Tiempo:** {position.exit_time.strftime('%Y-%m-%d %H:%M UTC') if position.exit_time else 'N/A'}"
            )
            
            self.telegram.send_message(message)
            logger.info(f"✅ Notificación de trailing stop enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de trailing stop: {str(e)}")
    
    async def send_brain_signal_exit(
        self, 
        position: TrendPosition, 
        directive: BrainDirective
    ) -> None:
        """Notifica salida por señal del cerebro."""
        try:
            pnl = position.realized_pnl()
            pnl_percent = float(pnl / (position.entry_price * position.entry_quantity) * 100)
            
            emoji = "✅" if pnl > 0 else "❌"
            
            message = (
                f"🧠 **SALIDA POR SEÑAL DEL CEREBRO** 🧠\n\n"
                f"🪙 **Par:** {position.symbol}\n"
                f"💰 **Precio Entrada:** ${position.entry_price:,.2f}\n"
                f"🏁 **Precio Salida:** ${position.exit_price:,.2f}\n"
                f"📦 **Cantidad:** {position.exit_quantity:.6f}\n"
                f"{emoji} **PnL:** ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
                f"💸 **Comisiones:** ${position.fees_paid:,.2f}\n"
                f"📝 **Decisión:** {directive.decision.value}\n"
                f"📋 **Razón:** {directive.reason or 'No especificada'}\n\n"
                f"⏰ **Tiempo:** {position.exit_time.strftime('%Y-%m-%d %H:%M UTC') if position.exit_time else 'N/A'}"
            )
            
            self.telegram.send_message(message)
            logger.info(f"✅ Notificación de señal del cerebro enviada para {position.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de señal del cerebro: {str(e)}")
    
    async def send_error_notification(
        self, 
        error: str, 
        details: Optional[Dict] = None
    ) -> None:
        """Envía notificación de error."""
        try:
            message = f"⚠️ **ERROR TREND BOT** ⚠️\n\n{error}"
            
            if details:
                message += "\n\n📋 **Detalles:**\n"
                for key, value in details.items():
                    message += f"• {key}: {value}\n"
            
            self.telegram.send_message(message)
            logger.info("✅ Alerta de error enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta de error: {str(e)}")
    
    async def send_startup_notification(self, config: TrendBotConfig) -> None:
        """Envía notificación de inicio del bot."""
        try:
            message = (
                f"🚀 **TREND BOT INICIADO** 🚀\n\n"
                f"🪙 **Par:** {config.symbol}\n"
                f"💰 **Capital:** ${config.capital_allocation:,.2f}\n"
                f"🛑 **Trailing Stop:** {config.trailing_stop_percent}%\n"
                f"🔧 **Modo:** {'Testnet' if config.sandbox_mode else 'Real'}\n\n"
                f"⏰ **Iniciado:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"📊 **Estrategia:** Seguimiento de tendencias a largo plazo\n"
                f"🔄 **Ciclo:** Cada 1 hora\n"
                f"🎯 **Objetivo:** Capturar movimientos direccionales del mercado"
            )
            
            self.telegram.send_message(message)
            logger.info("✅ Notificación de inicio enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {str(e)}") 