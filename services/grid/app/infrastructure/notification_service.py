"""
Servicio de notificaciones para Grid Trading.
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.interfaces import NotificationService
from app.domain.entities import GridTrade, GridConfig
from shared.services.telegram_trading import TelegramTradingService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class TelegramGridNotificationService(NotificationService):
    """Implementación de notificaciones usando Telegram."""

    def __init__(self):
        """Inicializa el servicio de notificaciones."""
        self.telegram_service = TelegramTradingService()
        
        # Control de spam para resúmenes periódicos
        self._last_summary_sent = {}
        self._summary_interval = timedelta(hours=2)  # Resumen cada 2 horas
        
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

    def send_info_notification(self, service_name: str, message: str) -> None:
        """Envía notificación informativa (no es un error)."""
        try:
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación informativa enviada para {service_name}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación informativa: {e}")

    def send_trade_notification(self, trade: GridTrade) -> None:
        """Envía notificación de una operación completada (DESHABILITADA para evitar spam)."""
        # NOTA: Esta notificación está deshabilitada para evitar spam
        # Los trades se reportan en los resúmenes periódicos cada 2 horas
        logger.debug(f"📊 Trade completado (sin notificación): {trade.pair} +${trade.profit:.4f}")
        pass

    def send_bot_status_notification(self, pair: str, status: str, reason: str) -> None:
        """Envía notificación de cambio de estado del bot."""
        try:
            message = f"""
🤖 CAMBIO DE ESTADO DEL BOT

📊 Par: {pair}
🔄 Estado: {status}
💭 Razón: {reason}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            self.telegram_service.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de estado: {e}")

    def send_grid_activation_notification(self, pair: str) -> None:
        """Envía notificación de activación de bot de grid."""
        try:
            message = f"""
🚀 BOT DE GRID ACTIVADO

📊 Par: {pair}
✅ Estado: ACTIVO
🏗️ Grilla inicial en creación
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

El bot comenzará a operar según las decisiones del Cerebro.
"""
            self.telegram_service.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de activación: {e}")

    def send_grid_pause_notification(self, pair: str, cancelled_orders: int) -> None:
        """Envía notificación de pausa de bot de grid."""
        try:
            message = f"""
⏸️ BOT DE GRID PAUSADO

📊 Par: {pair}
🛑 Estado: PAUSADO
🚫 Órdenes canceladas: {cancelled_orders}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

El bot se ha pausado según decisión del Cerebro.
"""
            self.telegram_service.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de pausa: {e}")

    def send_grid_summary(self, active_bots: int, total_trades: int, total_profit: float) -> None:
        """Envía resumen de actividad de grid trading."""
        try:
            message = f"""
📊 RESUMEN DE GRID TRADING

🤖 Bots activos: {active_bots}
🔄 Trades ejecutados: {total_trades}
💰 Ganancia total: ${total_profit:.4f} USDT
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Resumen del ciclo de monitoreo completado.
"""
            self.telegram_service.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando resumen de grid: {e}")

    def send_decision_change_notification(self, configs_with_decisions: List[tuple]) -> None:
        """
        Envía notificación cuando hay cambios de decisión en la base de datos.
        Se envía una sola vez por cambio de decisión para evitar spam.
        
        Args:
            configs_with_decisions: Lista de tuplas (GridConfig, current_decision, previous_state)
        """
        try:
            if not configs_with_decisions:
                return
            
            # Filtrar solo configuraciones con cambios de decisión
            changed_configs = []
            for config, current_decision, previous_state in configs_with_decisions:
                if current_decision != previous_state and current_decision != "NO_STRATEGY":
                    changed_configs.append((config, current_decision, previous_state))
            
            if not changed_configs:
                return
            
            # Crear mensaje de notificación
            message = "🔄 <b>CAMBIOS DE DECISIÓN - GRID TRADING</b>\n\n"
            
            for config, current_decision, previous_state in changed_configs:
                status_emoji = "✅" if current_decision == "RUNNING" else "⏸️"
                action = "INICIADO" if current_decision == "RUNNING" else "PAUSADO"
                
                message += f"{status_emoji} <b>{config.pair}</b>\n"
                message += f"   Estado anterior: {previous_state}\n"
                message += f"   Estado actual: {current_decision}\n"
                message += f"   Acción: {action}\n"
                message += f"   Capital: ${config.total_capital:.2f} USDT\n\n"
            
            message += f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de cambios de decisión enviada: {len(changed_configs)} bots")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de cambios de decisión: {e}")

    def send_periodic_trading_summary(self, trading_stats: Dict[str, Any]) -> bool:
        """
        Envía resumen periódico de trading (cada 2 horas).
        Controla el spam verificando el intervalo de tiempo.
        
        Args:
            trading_stats: Diccionario con estadísticas de trading
            
        Returns:
            bool: True si se envió la notificación, False si no se cumplió el intervalo
        """
        try:
            now = datetime.now()
            
            # Verificar si ha pasado suficiente tiempo desde el último resumen
            if 'last_summary_time' in self._last_summary_sent:
                time_since_last = now - self._last_summary_sent['last_summary_time']
                if time_since_last < self._summary_interval:
                    logger.debug(f"⏰ Resumen periódico no enviado: faltan {self._summary_interval - time_since_last}")
                    return False
            
            # Crear mensaje de resumen
            message = "📊 <b>RESUMEN PERIÓDICO - GRID TRADING</b>\n\n"
            
            # Balance total de la cuenta
            total_account_balance = trading_stats.get('total_account_balance', 0.0)
            message += f"💰 <b>Balance Total Cuenta:</b> ${total_account_balance:.2f} USDT\n\n"
            
            # Información general
            active_bots = trading_stats.get('active_bots', 0)
            total_trades = trading_stats.get('total_trades', 0)
            total_profit = trading_stats.get('total_profit', 0.0)
            
            message += f"🤖 <b>Bots Activos:</b> {active_bots}\n"
            message += f"🔄 <b>Trades Totales:</b> {total_trades}\n"
            message += f"💰 <b>Ganancia Total:</b> ${total_profit:.4f} USDT\n\n"
            
            # Detalles por par
            bots_details = trading_stats.get('bots_details', [])
            if bots_details:
                message += "📈 <b>DETALLES POR PAR:</b>\n\n"
                
                for bot_detail in bots_details:
                    pair = bot_detail.get('pair', 'N/A')
                    current_price = bot_detail.get('current_price', 0.0)
                    allocated_capital = bot_detail.get('allocated_capital', 0.0)
                    capital_in_assets = bot_detail.get('capital_in_assets', 0.0)
                    capital_in_assets_locked = bot_detail.get('capital_in_assets_locked', 0.0)
                    capital_in_usdt = bot_detail.get('capital_in_usdt', 0.0)
                    buy_orders = bot_detail.get('buy_orders', 0)
                    sell_orders = bot_detail.get('sell_orders', 0)
                    has_orders = bot_detail.get('has_orders', False)
                    pnl = bot_detail.get('pnl', 0.0)
                    pnl_percent = bot_detail.get('pnl_percent', 0.0)
                    
                    pnl_emoji = "💰" if pnl >= 0 else "📉"
                    
                    message += f"💱 <b>{pair}</b>\n"
                    message += f"   💵 Precio actual: ${current_price:.4f}\n"
                    message += f"   🏦 Capital asignado: ${allocated_capital:.2f}\n"
                    # Mostrar capital en activos con información de bloqueado
                    if capital_in_assets_locked > 0:
                        message += f"   🪙 Capital en activos: ${capital_in_assets:.2f} (bloqueado: ${capital_in_assets_locked:.2f})\n"
                    else:
                        message += f"   🪙 Capital en activos: ${capital_in_assets:.2f}\n"
                    message += f"   💵 Capital en USDT: ${capital_in_usdt:.2f}\n"
                    
                    # Mostrar órdenes de forma más clara con información de límite
                    if has_orders:
                        total_orders = buy_orders + sell_orders
                        # Obtener el límite de órdenes del bot (asumiendo que es grid_levels)
                        grid_levels = bot_detail.get('grid_levels', 30)  # Default 30 si no está disponible
                        
                        if total_orders >= grid_levels:
                            message += f"   📈 Órdenes compra: {buy_orders}\n"
                            message += f"   📉 Órdenes venta: {sell_orders}\n"
                            message += f"   🚦 Total órdenes: {total_orders}/{grid_levels} (límite alcanzado)\n"
                        else:
                            message += f"   📈 Órdenes compra: {buy_orders}\n"
                            message += f"   📉 Órdenes venta: {sell_orders}\n"
                            message += f"   📊 Total órdenes: {total_orders}/{grid_levels}\n"
                    else:
                        message += f"   ⏸️ Sin órdenes activas\n"
                    
                    message += f"   {pnl_emoji} P&L: ${pnl:.4f} ({pnl_percent:+.2f}%)\n\n"
            
            # Información de riesgo
            risk_events = trading_stats.get('risk_events', {})
            if risk_events:
                stop_loss_events = risk_events.get('stop_loss', 0)
                trailing_up_events = risk_events.get('trailing_up', 0)
                
                if stop_loss_events > 0 or trailing_up_events > 0:
                    message += "🛡️ <b>EVENTOS DE RIESGO:</b>\n"
                    message += f"   🚨 Stop Loss: {stop_loss_events}\n"
                    message += f"   📈 Trailing Up: {trailing_up_events}\n\n"
            
            # 📱 Información de órdenes complementarias acumuladas
            complementary_orders_summary = trading_stats.get('complementary_orders_summary', '')
            if complementary_orders_summary:
                message += f"{complementary_orders_summary}\n\n"
            
            message += f"⏰ <i>{now.strftime('%H:%M:%S %d/%m/%Y')}</i>\n"
            message += f"🔄 <i>Resumen cada 2 horas</i>"
            
            # Enviar mensaje
            self.telegram_service.send_message(message)
            
            # Actualizar timestamp del último resumen
            self._last_summary_sent['last_summary_time'] = now
            
            logger.info(f"✅ Resumen periódico enviado: {active_bots} bots activos, ${total_profit:.4f} ganancia, Balance total: ${total_account_balance:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando resumen periódico: {e}")
            return False

    def send_risk_event_notification(self, event_type: str, pair: str, details: Dict[str, Any]) -> None:
        """
        Envía notificación específica para eventos de riesgo (stop loss, trailing up).
        
        Args:
            event_type: 'stop_loss' o 'trailing_up'
            pair: Par de trading
            details: Detalles del evento
        """
        try:
            if event_type == 'stop_loss':
                emoji = "🚨"
                title = "STOP LOSS ACTIVADO"
                color = "🔴"
            elif event_type == 'trailing_up':
                emoji = "📈"
                title = "TRAILING UP ACTIVADO"
                color = "🟢"
            else:
                return
            
            message = f"{emoji} <b>{title}</b>\n\n"
            message += f"💱 <b>Par:</b> {pair}\n"
            
            if event_type == 'stop_loss':
                last_buy_price = details.get('last_buy_price', 0)
                current_price = details.get('current_price', 0)
                drop_percent = details.get('drop_percent', 0)
                
                message += f"📉 <b>Última compra:</b> ${last_buy_price:.4f}\n"
                message += f"📊 <b>Precio actual:</b> ${current_price:.4f}\n"
                message += f"📉 <b>Caída:</b> {drop_percent:.2f}%\n"
                message += f"🛑 <b>Acción:</b> Liquidación y pausa del bot\n"
                
            elif event_type == 'trailing_up':
                highest_sell_price = details.get('highest_sell_price', 0)
                current_price = details.get('current_price', 0)
                rise_percent = details.get('rise_percent', 0)
                
                message += f"📈 <b>Nivel más alto venta:</b> ${highest_sell_price:.4f}\n"
                message += f"📊 <b>Precio actual:</b> ${current_price:.4f}\n"
                message += f"📈 <b>Subida:</b> {rise_percent:.2f}%\n"
                message += f"🔄 <b>Acción:</b> Reinicio con nuevo precio base\n"
            
            message += f"\n⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            self.telegram_service.send_message(message)
            logger.info(f"✅ Notificación de evento de riesgo enviada: {event_type} para {pair}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de evento de riesgo: {e}")

    def set_summary_interval(self, hours: int) -> None:
        """
        Configura el intervalo para resúmenes periódicos.
        
        Args:
            hours: Número de horas entre resúmenes
        """
        self._summary_interval = timedelta(hours=hours)
        logger.info(f"✅ Intervalo de resúmenes configurado: {hours} horas")

    def force_send_summary(self) -> bool:
        """
        Fuerza el envío de un resumen inmediatamente, ignorando el intervalo.
        Útil para testing o solicitudes manuales.
        """
        # Limpiar timestamp para forzar envío
        if 'last_summary_time' in self._last_summary_sent:
            del self._last_summary_sent['last_summary_time']
        
        logger.info("✅ Forzando envío de resumen inmediato")
        return True

    def send_notification(self, message: str) -> None:
        """
        Envía una notificación genérica por Telegram.
        
        Args:
            message: Mensaje a enviar
        """
        try:
            self.telegram_service.send_message(message)
            logger.info("✅ Notificación genérica enviada")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación genérica: {e}")

    def send_detailed_status_notification(self, summary) -> None:
        """
        Envía notificación con el estado detallado de trading.
        
        Args:
            summary: Objeto TradingSummary con el estado detallado
        """
        try:
            message = self._format_detailed_status_message(summary)
            self.telegram_service.send_message(message)
            logger.info("✅ Notificación de estado detallado enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de estado detallado: {e}")

    def send_restart_safety_notification(self, report) -> None:
        """
        Envía notificación con el reporte de seguridad al reiniciar.
        
        Args:
            report: Objeto RestartSafetyReport con el reporte de seguridad
        """
        try:
            message = self._format_safety_report_message(report)
            self.telegram_service.send_message(message)
            logger.info("✅ Notificación de reporte de seguridad enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de seguridad: {e}")

    def _format_detailed_status_message(self, summary) -> str:
        """
        Formatea el resumen detallado como mensaje legible.
        
        Args:
            summary: Resumen del estado de trading
            
        Returns:
            str: Mensaje formateado
        """
        try:
            message = f"📊 **ESTADO DETALLADO DE TRADING**\n\n"
            message += f"🕐 Actualizado: {summary.last_update.strftime('%H:%M:%S %d/%m/%Y')}\n"
            message += f"💱 Modo: {summary.trading_mode.upper()}\n\n"
            
            # Resumen general
            message += f"**📈 RESUMEN GENERAL**\n"
            message += f"• Total de bots: {summary.total_bots}\n"
            message += f"• Bots activos: {summary.active_bots} 🟢\n"
            message += f"• Bots pausados: {summary.paused_bots} ⏸️\n"
            message += f"• Capital asignado: ${summary.total_capital_allocated:,.2f} USDT\n"
            message += f"• Capital disponible: ${summary.total_capital_available:,.2f} USDT\n"
            message += f"• Órdenes activas: {summary.total_orders_active}\n\n"
            
            # Balance del exchange
            message += f"**💰 BALANCE DEL EXCHANGE**\n"
            for currency, amount in summary.exchange_balance.items():
                if amount > 0:
                    message += f"• {currency}: {amount:,.8f}\n"
            message += "\n"
            
            # Estado de cada bot
            message += f"**🤖 ESTADO DE BOTS**\n"
            for bot in summary.bots_status:
                if bot.is_active:  # Solo mostrar bots activos
                    message += f"\n**{bot.pair}** {bot.status_summary}\n"
                    message += f"• Capital: ${bot.allocated_capital:,.2f} USDT\n"
                    message += f"• Precio actual: ${bot.current_price:,.8f}\n"
                    message += f"• Niveles: {bot.grid_levels} | Rango: {bot.price_range_percent}%\n"
                    message += f"• Órdenes activas: {bot.active_orders_count}\n"
                    message += f"• Última decisión: {bot.last_decision}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando mensaje de estado: {e}")
            return f"❌ Error generando estado detallado: {e}"

    def _format_safety_report_message(self, report) -> str:
        """
        Formatea el reporte de seguridad como mensaje legible.
        
        Args:
            report: Reporte de seguridad
            
        Returns:
            str: Mensaje formateado
        """
        try:
            message = f"🔒 **REPORTE DE SEGURIDAD AL REINICIAR**\n\n"
            
            # Resumen general
            message += f"**📊 RESUMEN GENERAL**\n"
            message += f"• Órdenes canceladas: {report.total_orders_cancelled}\n"
            message += f"• Capital faltante total: ${report.total_missing_capital:,.2f} USDT\n"
            message += f"• Capital excedente total: ${report.total_excess_capital:,.2f} USDT\n"
            message += f"• Seguro para continuar: {'✅ SÍ' if report.is_safe_to_continue else '❌ NO'}\n\n"
            
            # Verificaciones por par
            message += f"**💰 VERIFICACIÓN POR PAR**\n"
            for verification in report.capital_verifications:
                message += f"\n**{verification.pair}**\n"
                message += f"• Capital asignado: ${verification.allocated_capital:,.2f} USDT\n"
                message += f"• Balance USDT: ${verification.actual_balance_usdt:,.2f}\n"
                message += f"• Balance {verification.pair.split('/')[0]}: {verification.actual_balance_crypto:,.8f}\n"
                message += f"• Valor total: ${verification.total_value:,.2f} USDT\n"
                
                if verification.missing_capital > 0:
                    message += f"• ⚠️ Capital faltante: ${verification.missing_capital:,.2f}\n"
                if verification.excess_capital > 0:
                    message += f"• 💰 Capital excedente: ${verification.excess_capital:,.2f}\n"
                
                message += f"• Estado: {'✅ SEGURO' if verification.is_safe else '❌ INSEGURO'}\n"
            
            # Recomendaciones
            if report.recommendations:
                message += f"\n**💡 RECOMENDACIONES**\n"
                for rec in report.recommendations:
                    message += f"• {rec}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando reporte de seguridad: {e}")
            return f"❌ Error generando reporte de seguridad: {e}" 