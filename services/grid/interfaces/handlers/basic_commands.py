"""
Handler para comandos básicos del Grid Bot.
Maneja comandos como start, status, delete_config, etc.
"""
import threading
import time
from datetime import datetime

from shared.services.telegram_bot_service import TelegramBot
from services.grid.schedulers.grid_scheduler import (
    get_grid_scheduler,
    start_grid_bot_scheduler, 
    stop_grid_bot_scheduler,
    start_grid_bot_manual,
    stop_grid_bot_manual,
    get_grid_bot_status
)
from .base_handler import BaseHandler


class BasicCommandsHandler(BaseHandler):
    """Handler para comandos básicos del Grid Bot"""
    
    def handle_start_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start"""
        try:
            # Limpiar estados de conversación
            bot.clear_conversation_state(chat_id)
            
            message = "🤖 <b>¡Bienvenido al Oráculo Grid Bot!</b>\n\n"
            message += "🎯 <b>¿Qué puedes hacer?</b>\n"
            message += "• Configurar estrategias de trading automáticas\n"
            message += "• Controlar el bot desde Telegram\n"
            message += "• Monitorear tus trades en tiempo real\n\n"
            
            # Verificar estado actual
            scheduler = get_grid_scheduler()
            if scheduler and scheduler.running:
                message += "🟢 <b>Estado:</b> Bot ejecutándose\n"
            else:
                message += "🔴 <b>Estado:</b> Bot detenido\n"
            
            # Verificar si tiene configuración guardada
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"⚙️ <b>Configuración:</b> {user_config.pair} con ${user_config.total_capital}\n"
            else:
                message += "⚙️ <b>Configuración:</b> No configurado\n"
            
            message += "\n📋 <b>Comandos disponibles:</b>\n"
            message += "/config - Configurar bot paso a paso\n"
            message += "/start_bot - Iniciar trading\n"
            message += "/stop_bot - Detener bot\n"
            message += "/restart_bot - Reiniciar con nueva config\n"
            message += "/status - Ver estado detallado\n"
            message += "/delete_config - Borrar configuración\n\n"
            message += "🛡️ <b>Comandos V2 - Estrategias Avanzadas:</b>\n"
            message += "/protections - Ver estado de protecciones\n"
            message += "/enable_stop_loss - Activar stop-loss\n"
            message += "/disable_stop_loss - Desactivar stop-loss\n"
            message += "/enable_trailing - Activar trailing up\n"
            message += "/disable_trailing - Desactivar trailing up\n"
            message += "/set_stop_loss X - Configurar % de stop-loss\n"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "comando start", e)
    
    def handle_start_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start_bot - V2 con modo manual"""
        try:
            # Verificar configuración
            user_config = self.get_user_config(chat_id)
            if not user_config:
                message = "⚠️ <b>No tienes configuración guardada</b>\n\n"
                message += "Usa /config para configurar el bot primero."
                bot.send_message(chat_id, message)
                return
            
            # Verificar estado del bot
            bot_status = get_grid_bot_status()
            if bot_status['bot_running']:
                bot.send_message(chat_id, "⚠️ El bot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            if not bot_status['ready_to_start']:
                message = "⚠️ <b>Servicio no está listo</b>\n\n"
                message += "El scheduler no está activo. Contacta al administrador."
                bot.send_message(chat_id, message)
                return
            
            # Iniciar bot manualmente
            def start_bot_async():
                try:
                    success, result_message = start_grid_bot_manual()
                    
                    if success:
                        message = f"🚀 <b>¡Grid Bot iniciado exitosamente!</b>\n\n"
                        message += f"📊 <b>Trading:</b> {user_config.pair}\n"
                        message += f"💰 <b>Capital:</b> ${user_config.total_capital} USDT\n"
                        message += f"🎚️ <b>Niveles:</b> {user_config.grid_levels}\n"
                        message += f"📊 <b>Rango:</b> ±{user_config.price_range_percent}%\n\n"
                        message += f"🛡️ <b>Protecciones V2:</b>\n"
                        message += f"• Stop-Loss: {'✅' if getattr(user_config, 'enable_stop_loss', True) else '❌'} ({getattr(user_config, 'stop_loss_percent', 5.0)}%)\n"
                        message += f"• Trailing Up: {'✅' if getattr(user_config, 'enable_trailing_up', True) else '❌'}\n\n"
                        message += f"📈 Usa /status para monitorear el progreso."
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ <b>Error iniciando bot:</b> {result_message}")
                        
                except Exception as e:
                    self.send_error_message(bot, chat_id, "start_bot_async", e)
            
            threading.Thread(target=start_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "start_bot", e)
    
    def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /stop_bot - V2 con modo manual"""
        try:
            # Verificar estado del bot
            bot_status = get_grid_bot_status()
            if not bot_status['bot_running']:
                bot.send_message(chat_id, "ℹ️ El bot ya está detenido (modo standby).")
                return
            
            if not bot_status['ready_to_stop']:
                message = "⚠️ <b>No se puede detener el bot</b>\n\n"
                message += "El bot no está en un estado válido para detener."
                bot.send_message(chat_id, message)
                return
            
            def stop_bot_async():
                try:
                    success, result_message = stop_grid_bot_manual()
                    
                    if success:
                        message = "🛑 <b>Grid Bot detenido correctamente</b>\n\n"
                        message += "✅ Se señaló la parada del bot\n"
                        message += "🧹 Las órdenes serán canceladas automáticamente\n"
                        message += "⏸️ Bot entrando en modo standby\n\n"
                        message += "ℹ️ <i>El proceso de cancelación puede tomar unos segundos</i>\n"
                        message += "▶️ Usa /start_bot para reanudar trading"
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ <b>Error deteniendo bot:</b> {result_message}")
                        
                except Exception as e:
                    self.send_error_message(bot, chat_id, "stop_bot_async", e)
            
            threading.Thread(target=stop_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Deteniendo Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "stop_bot", e)
    
    def handle_restart_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /restart_bot"""
        try:
            def restart_bot_async():
                try:
                    # Detener si está ejecutándose
                    scheduler = get_grid_scheduler()
                    if scheduler and scheduler.running:
                        bot.send_message(chat_id, "🛑 Deteniendo bot actual...")
                        stop_grid_bot_scheduler()
                        time.sleep(3)  # Esperar un poco
                    
                    # Iniciar de nuevo
                    bot.send_message(chat_id, "🚀 Reiniciando bot...")
                    start_grid_bot_scheduler()
                    
                    user_config = self.get_user_config(chat_id)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>Bot reiniciado correctamente</b>\n\n"
                        f"📊 Trading: {user_config.pair if user_config else 'N/A'}\n"
                        f"Usa /status para verificar el estado."
                    )
                    
                except Exception as e:
                    self.send_error_message(bot, chat_id, "reiniciando bot", e)
            
            threading.Thread(target=restart_bot_async, daemon=True).start()
            bot.send_message(chat_id, "🔄 Reiniciando Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "restart_bot", e)
    
    def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /status - V2 con modo standby"""
        try:
            bot_status = get_grid_bot_status()
            
            message = "📊 <b>ESTADO DEL GRID BOT V2</b>\n\n"
            
            # Estado principal
            if bot_status['bot_running']:
                message += "🟢 <b>Estado:</b> EJECUTÁNDOSE\n"
                message += "📈 Trading activo\n"
            elif bot_status['standby_mode']:
                message += "⏸️ <b>Estado:</b> MODO STANDBY\n"
                message += "🛡️ Servicio activo, esperando comando\n"
            else:
                message += "🔴 <b>Estado:</b> DETENIDO\n"
                message += "❌ Servicio inactivo\n"
            
            # Estado técnico
            message += f"\n🔧 <b>Estado técnico:</b>\n"
            message += f"• Scheduler: {'✅' if bot_status['scheduler_active'] else '❌'}\n"
            message += f"• Bot trading: {'✅' if bot_status['bot_running'] else '❌'}\n"
            message += f"• Hilo activo: {'✅' if bot_status['thread_alive'] else '❌'}\n"
            
            # Mostrar configuración del usuario
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"\n⚙️ <b>Configuración actual:</b>\n"
                message += f"📈 <b>Par:</b> {user_config.pair}\n"
                message += f"💰 <b>Capital:</b> ${user_config.total_capital} USDT\n"
                message += f"🎚️ <b>Niveles:</b> {user_config.grid_levels}\n"
                message += f"📊 <b>Rango:</b> ±{user_config.price_range_percent}%\n"
                
                # Protecciones V2
                message += f"\n🛡️ <b>Protecciones V2:</b>\n"
                message += f"• Stop-Loss: {'✅' if getattr(user_config, 'enable_stop_loss', True) else '❌'} ({getattr(user_config, 'stop_loss_percent', 5.0)}%)\n"
                message += f"• Trailing Up: {'✅' if getattr(user_config, 'enable_trailing_up', True) else '❌'}\n"
                
                message += f"\n📅 <b>Creado:</b> {user_config.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                message += "\n⚠️ <b>Sin configuración guardada</b>\n"
                message += "Usa /config para configurar el bot\n"
            
            # Acciones disponibles
            message += f"\n🎮 <b>Acciones disponibles:</b>\n"
            if bot_status['ready_to_start']:
                message += "▶️ /start_bot - Iniciar trading\n"
            if bot_status['ready_to_stop']:
                message += "⏸️ /stop_bot - Detener trading\n"
            message += "🔄 /restart_bot - Reiniciar con nueva config\n"
            message += "🛡️ /protections - Ver estrategias avanzadas\n"
            
            message += f"\n⏰ <i>Consultado: {datetime.now().strftime('%H:%M:%S')}</i>"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "status", e)
    
    def handle_delete_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /delete_config"""
        try:
            user_config = self.get_user_config(chat_id)
            
            if not user_config:
                bot.send_message(chat_id, "ℹ️ No tienes configuración guardada.")
                return
            
            # Desactivar configuración en la base de datos
            if self.update_user_config(chat_id, {'is_active': False}):
                bot.send_message(
                    chat_id, 
                    f"✅ Configuración eliminada correctamente.\n\n"
                    f"Se eliminó: {user_config.pair} con ${user_config.total_capital} USDT"
                )
            else:
                bot.send_message(chat_id, "❌ Error eliminando configuración")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "eliminando config", e) 