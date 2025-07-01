"""
Handler para estrategias avanzadas del Grid Bot V2.
Maneja comandos relacionados con stop-loss, trailing up y protecciones.
"""
from shared.services.telegram_bot_service import TelegramBot
from .base_handler import BaseHandler


class AdvancedStrategiesHandler(BaseHandler):
    """Handler para estrategias avanzadas del Grid Bot V2"""
    
    async def handle_enable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /enable_stop_loss"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            # Actualizar en base de datos
            if self.update_user_config(chat_id, {'enable_stop_loss': True}):
                message = "🛡️ <b>STOP-LOSS ACTIVADO</b>\n\n"
                message += f"📉 Se activará si el precio baja {getattr(user_config, 'stop_loss_percent', 5.0)}% debajo del nivel más bajo\n"
                message += f"⚠️ El bot se detendrá automáticamente si se activa\n\n"
                message += f"💡 Usa /set_stop_loss X para cambiar el porcentaje"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ Error activando stop-loss")
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "habilitando stop-loss", e)

    async def handle_disable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /disable_stop_loss"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            # Actualizar en base de datos
            if self.update_user_config(chat_id, {'enable_stop_loss': False}):
                message = "🚫 <b>STOP-LOSS DESACTIVADO</b>\n\n"
                message += f"⚠️ <b>ATENCIÓN:</b> El bot NO se protegerá contra caídas bruscas\n"
                message += f"💡 Usa /enable_stop_loss para reactivar la protección"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ Error desactivando stop-loss")
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "deshabilitando stop-loss", e)

    async def handle_enable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /enable_trailing"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            # Actualizar en base de datos
            if self.update_user_config(chat_id, {'enable_trailing_up': True}):
                message = "📈 <b>TRAILING UP ACTIVADO</b>\n\n"
                message += f"🚀 El bot seguirá tendencias alcistas automáticamente\n"
                message += f"🎯 Reposicionará el grid si el precio rompe el límite superior\n\n"
                message += f"💡 Esto mantiene al bot activo en mercados alcistas"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ Error activando trailing up")
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "habilitando trailing up", e)

    async def handle_disable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /disable_trailing"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            # Actualizar en base de datos
            if self.update_user_config(chat_id, {'enable_trailing_up': False}):
                message = "🚫 <b>TRAILING UP DESACTIVADO</b>\n\n"
                message += f"📊 El bot mantendrá su grid fijo sin reposicionarse\n"
                message += f"⚠️ Puede quedarse fuera del mercado en tendencias alcistas\n\n"
                message += f"💡 Usa /enable_trailing para reactivar"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ Error desactivando trailing up")
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "deshabilitando trailing up", e)

    async def handle_set_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /set_stop_loss X"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            # Extraer porcentaje del mensaje
            parts = message_text.strip().split()
            if len(parts) != 2:
                await bot.send_message(
                    chat_id, 
                    "❌ Formato incorrecto.\n\n"
                    "✅ Uso correcto: <code>/set_stop_loss 3.5</code>\n"
                    "💡 Ejemplo: 3.5 significa 3.5% de pérdida máxima"
                )
                return
            
            try:
                new_percentage = float(parts[1])
                if new_percentage < 0.1 or new_percentage > 20:
                    await bot.send_message(
                        chat_id,
                        "❌ El porcentaje debe estar entre 0.1% y 20%\n\n"
                        "💡 Valores recomendados:\n"
                        "• Conservador: 2-3%\n"
                        "• Moderado: 4-6%\n"
                        "• Agresivo: 7-10%"
                    )
                    return
            except ValueError:
                await bot.send_message(chat_id, "❌ Porcentaje inválido. Usa números como: 3.5")
                return
            
            # Actualizar en base de datos
            updates = {
                'stop_loss_percent': new_percentage,
                'enable_stop_loss': True  # Activar automáticamente al configurar
            }
            
            if self.update_user_config(chat_id, updates):
                message = f"✅ <b>STOP-LOSS CONFIGURADO</b>\n\n"
                message += f"📉 <b>Nuevo porcentaje:</b> {new_percentage}%\n"
                message += f"🛡️ <b>Estado:</b> Activado automáticamente\n\n"
                message += f"💡 El bot se detendrá si el precio baja {new_percentage}% debajo del nivel más bajo"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ Error configurando stop-loss")
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "configurando stop-loss", e)

    async def handle_protections_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /protections"""
        try:
            user_config = self.validate_config_exists(bot, chat_id)
            if not user_config:
                return
            
            message = "🛡️ <b>ESTADO DE PROTECCIONES V2</b>\n\n"
            
            # Stop-Loss
            stop_loss_enabled = getattr(user_config, 'enable_stop_loss', True)
            stop_loss_percent = getattr(user_config, 'stop_loss_percent', 5.0)
            
            if stop_loss_enabled:
                message += f"🟢 <b>Stop-Loss:</b> ACTIVO ({stop_loss_percent}%)\n"
                message += f"   📉 Se activará si baja {stop_loss_percent}% del nivel más bajo\n\n"
            else:
                message += f"🔴 <b>Stop-Loss:</b> INACTIVO\n"
                message += f"   ⚠️ Sin protección contra caídas bruscas\n\n"
            
            # Trailing Up
            trailing_enabled = getattr(user_config, 'enable_trailing_up', True)
            
            if trailing_enabled:
                message += f"🟢 <b>Trailing Up:</b> ACTIVO\n"
                message += f"   📈 Seguirá tendencias alcistas automáticamente\n\n"
            else:
                message += f"🔴 <b>Trailing Up:</b> INACTIVO\n"
                message += f"   📊 Grid fijo, puede perderse rallies\n\n"
            
            message += "🔧 <b>Comandos disponibles:</b>\n"
            message += "/enable_stop_loss - Activar protección\n"
            message += "/disable_stop_loss - Desactivar protección\n"
            message += "/enable_trailing - Activar seguimiento\n"
            message += "/disable_trailing - Desactivar seguimiento\n"
            message += "/set_stop_loss X - Configurar porcentaje\n\n"
            
            message += f"📊 <b>Configuración actual:</b>\n"
            message += f"Par: {user_config.pair} | Capital: ${user_config.total_capital}\n"
            message += f"Niveles: {user_config.grid_levels} | Rango: ±{user_config.price_range_percent}%"
            
            await bot.send_message(chat_id, message)
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "mostrando protecciones", e) 