"""
Handler para comandos del sistema multibot simultáneo.
Maneja comandos para controlar múltiples bots ejecutándose al mismo tiempo.
"""

import threading
from datetime import datetime
from typing import Dict, Any

from shared.services.telegram_bot_service import TelegramBot
from shared.services.logging_config import get_logger
from services.grid.schedulers.multibot_scheduler import get_multibot_scheduler
from .base_handler import BaseHandler

logger = get_logger(__name__)

class MultibotCommandsHandler(BaseHandler):
    """Handler para comandos del sistema multibot simultáneo"""
    
    def handle_start_multibot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Comando /start_multibot: Inicia todos los bots configurados simultáneamente"""
        try:
            # Obtener configuraciones activas
            active_configs = self.get_all_user_configs(chat_id)
            configured_configs = [config for config in active_configs if getattr(config, 'is_configured', False)]
            
            if not configured_configs:
                message = "⚠️ <b>No hay configuraciones activas</b>\n\n"
                message += "💡 Usa /config para configurar al menos un par primero"
                bot.send_message(chat_id, message)
                return
            
            # Obtener scheduler multibot
            scheduler = get_multibot_scheduler()
            
            def start_multibot_async():
                try:
                    bot.send_message(chat_id, "🚀 Iniciando sistema multibot simultáneo...")
                    
                    started_bots = []
                    failed_bots = []
                    
                    for config in configured_configs:
                        try:
                            pair = config.pair
                            config_dict = config.to_dict()
                            
                            # Iniciar bot para este par
                            if scheduler.start_bot_for_pair(pair, config_dict):
                                started_bots.append(config.config_type)
                                bot.send_message(chat_id, f"✅ Bot {config.config_type} iniciado")
                            else:
                                failed_bots.append(config.config_type)
                                bot.send_message(chat_id, f"❌ Error iniciando bot {config.config_type}")
                                
                        except Exception as e:
                            failed_bots.append(config.config_type)
                            logger.error(f"❌ Error iniciando bot {config.config_type}: {e}")
                            bot.send_message(chat_id, f"❌ Error iniciando bot {config.config_type}: {str(e)}")
                    
                    # Resumen final
                    message = "🤖 <b>SISTEMA MULTIBOT SIMULTÁNEO</b>\n\n"
                    
                    if started_bots:
                        message += f"✅ <b>Bots iniciados ({len(started_bots)}):</b>\n"
                        for bot_type in started_bots:
                            message += f"• {bot_type}\n"
                        message += "\n"
                    
                    if failed_bots:
                        message += f"❌ <b>Bots con error ({len(failed_bots)}):</b>\n"
                        for bot_type in failed_bots:
                            message += f"• {bot_type}\n"
                        message += "\n"
                    
                    message += "📊 <b>Estado del sistema:</b>\n"
                    message += f"• Total configurados: {len(configured_configs)}\n"
                    message += f"• Ejecutándose: {len(started_bots)}\n"
                    message += f"• Con errores: {len(failed_bots)}\n\n"
                    
                    message += "🧠 <b>Recetas maestras activas:</b>\n"
                    for config in configured_configs:
                        recipe_info = self._get_recipe_info(config.pair)
                        message += f"• {config.config_type}: {recipe_info}\n"
                    
                    message += "\n📈 Usa /status_multibot para monitorear todos los bots"
                    
                    bot.send_message(chat_id, message)
                    
                except Exception as e:
                    logger.error(f"❌ Error en start_multibot_async: {e}")
                    bot.send_message(chat_id, f"❌ Error iniciando sistema multibot: {str(e)}")
            
            threading.Thread(target=start_multibot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando sistema multibot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "start_multibot", e)
    
    def handle_stop_multibot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Comando /stop_multibot: Detiene todos los bots activos"""
        try:
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()
            
            if status['total_active_bots'] == 0:
                bot.send_message(chat_id, "ℹ️ No hay bots ejecutándose actualmente")
                return
            
            def stop_multibot_async():
                try:
                    bot.send_message(chat_id, f"🛑 Deteniendo {status['total_active_bots']} bots activos...")
                    
                    # Detener todos los bots
                    scheduler.stop_all_bots()
                    
                    message = "✅ <b>SISTEMA MULTIBOT DETENIDO</b>\n\n"
                    message += f"🛑 <b>Bots detenidos:</b> {status['total_active_bots']}\n"
                    message += "⏸️ Todos los bots están en modo standby\n\n"
                    message += "🚀 Usa /start_multibot para reiniciar el sistema"
                    
                    bot.send_message(chat_id, message)
                    
                except Exception as e:
                    logger.error(f"❌ Error en stop_multibot_async: {e}")
                    bot.send_message(chat_id, f"❌ Error deteniendo sistema multibot: {str(e)}")
            
            threading.Thread(target=stop_multibot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Deteniendo sistema multibot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "stop_multibot", e)
    
    def handle_status_multibot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Comando /status_multibot: Muestra el estado de todos los bots"""
        try:
            # Obtener estado del scheduler
            scheduler = get_multibot_scheduler()
            scheduler_status = scheduler.get_status()
            
            # Obtener configuraciones del usuario
            all_configs = self.get_all_user_configs(chat_id)
            
            message = "🤖 <b>ESTADO DEL SISTEMA MULTIBOT SIMULTÁNEO</b>\n\n"
            
            # Estado del scheduler
            scheduler_icon = "🟢" if scheduler_status['scheduler_running'] else "🔴"
            message += f"{scheduler_icon} <b>Scheduler:</b> {'Activo' if scheduler_status['scheduler_running'] else 'Inactivo'}\n"
            message += f"📊 <b>Bots ejecutándose:</b> {scheduler_status['total_active_bots']}\n\n"
            
            # Estado de cada configuración
            message += "📋 <b>Estado por configuración:</b>\n"
            
            for config in all_configs:
                config_type = config.config_type
                is_configured = getattr(config, 'is_configured', False)
                is_running = getattr(config, 'is_running', False)
                last_decision = getattr(config, 'last_decision', 'NO_DECISION')
                
                if is_configured:
                    status_icon = "🟢" if is_running else "🔴"
                    decision_icon = "✅" if last_decision == 'OPERAR_GRID' else "❌"
                    
                    message += f"{status_icon} <b>{config_type}:</b>\n"
                    message += f"   📊 Par: {config.pair}\n"
                    message += f"   💰 Capital: ${config.total_capital}\n"
                    message += f"   🎯 Niveles: {config.grid_levels}\n"
                    message += f"   📈 Rango: ±{config.price_range_percent}%\n"
                    message += f"   🧠 Decisión: {decision_icon} {last_decision}\n"
                    message += f"   🤖 Estado: {'Ejecutándose' if is_running else 'Detenido'}\n\n"
                else:
                    message += f"⚪ <b>{config_type}:</b> Sin configurar\n\n"
            
            # Información de recetas maestras
            message += "🧠 <b>Recetas Maestras:</b>\n"
            message += "• ETH: ADX < 30, Bollinger > 0.025, Rango 10%\n"
            message += "• BTC: ADX < 25, Bollinger > 0.035, Rango 7.5%\n"
            message += "• AVAX: ADX < 35, Bollinger > 0.020, Rango 10%\n\n"
            
            # Comandos disponibles
            message += "🔧 <b>Comandos disponibles:</b>\n"
            message += "/start_multibot - Iniciar todos los bots\n"
            message += "/stop_multibot - Detener todos los bots\n"
            message += "/config - Configurar bots\n"
            message += "/balance_multibot - Ver balance de todos los pares\n"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "status_multibot", e)
    
    def handle_balance_multibot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Comando /balance_multibot: Muestra el balance de todos los pares configurados"""
        try:
            # Obtener configuraciones activas
            active_configs = self.get_all_user_configs(chat_id)
            configured_configs = [config for config in active_configs if getattr(config, 'is_configured', False)]
            
            if not configured_configs:
                bot.send_message(chat_id, "⚠️ No hay configuraciones activas. Usa /config primero.")
                return
            
            def get_balance_multibot_async():
                try:
                    bot.send_message(chat_id, "⏳ Obteniendo balances de todos los pares...")
                    
                    from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
                    from services.grid.core.config_manager import get_exchange_connection
                    from shared.services.telegram_service import get_current_balance, calculate_pnl_with_explanation
                    
                    exchange = get_exchange_connection()
                    modo_info = "🟢 PRODUCTIVO" if MODO_PRODUCTIVO else "🟡 SANDBOX"
                    
                    message = f"💰 <b>BALANCE MULTIBOT SIMULTÁNEO</b>\n\n{modo_info}\n\n"
                    
                    total_pnl = 0.0
                    total_initial_capital = 0.0
                    
                    for config in configured_configs:
                        try:
                            pair = config.pair
                            initial_capital = config.total_capital
                            
                            # Obtener balance actual
                            balance = get_current_balance(exchange, pair)
                            
                            # Calcular P&L
                            mode = "PRODUCTIVO" if MODO_PRODUCTIVO else "SANDBOX"
                            pnl_data = calculate_pnl_with_explanation(balance, initial_capital, mode)
                            
                            message += f"📊 <b>{config.config_type}:</b>\n"
                            message += f"   💵 USDT: ${balance['usdt']:.2f}\n"
                            message += f"   🪙 {balance['crypto_symbol']}: {balance['crypto']:.6f}\n"
                            message += f"   💎 Valor: ${balance['crypto_value']:.2f}\n"
                            message += f"   📊 Total: ${balance['total_value']:.2f}\n"
                            message += f"   {pnl_data['pnl_icon']} P&L: ${pnl_data['total_pnl']:.2f} ({pnl_data['total_pnl_percentage']:.2f}%)\n\n"
                            
                            total_pnl += pnl_data['total_pnl']
                            total_initial_capital += initial_capital
                            
                        except Exception as e:
                            message += f"❌ <b>{config.config_type}:</b> Error obteniendo balance\n\n"
                            logger.error(f"❌ Error obteniendo balance para {config.config_type}: {e}")
                    
                    # Resumen total
                    if total_initial_capital > 0:
                        total_pnl_percentage = (total_pnl / total_initial_capital) * 100
                        total_pnl_icon = "📈" if total_pnl >= 0 else "📉"
                        
                        message += f"📊 <b>RESUMEN TOTAL:</b>\n"
                        message += f"   💰 Capital inicial: ${total_initial_capital:.2f}\n"
                        message += f"   {total_pnl_icon} P&L total: ${total_pnl:.2f} ({total_pnl_percentage:.2f}%)\n"
                        message += f"   📊 Pares activos: {len(configured_configs)}\n\n"
                    
                    message += f"⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
                    
                    bot.send_message(chat_id, message)
                    
                except Exception as e:
                    logger.error(f"❌ Error en get_balance_multibot_async: {e}")
                    bot.send_message(chat_id, f"❌ Error obteniendo balances: {str(e)}")
            
            threading.Thread(target=get_balance_multibot_async, daemon=True).start()
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "balance_multibot", e)
    
    def _get_recipe_info(self, pair: str) -> str:
        """Obtiene información de la receta maestra para un par"""
        recipes = {
            'ETH/USDT': 'ADX < 30, Bollinger > 0.025, Rango 10%',
            'BTC/USDT': 'ADX < 25, Bollinger > 0.035, Rango 7.5%',
            'AVAX/USDT': 'ADX < 35, Bollinger > 0.020, Rango 10%'
        }
        return recipes.get(pair, 'Receta no definida') 