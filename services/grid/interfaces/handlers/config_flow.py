"""
Handler para el flujo de configuración del Grid Bot.
Maneja el proceso paso a paso de configuración: selección de par, capital, confirmación.
"""
from shared.services.telegram_bot_service import TelegramBot
from .base_handler import BaseHandler


class ConfigFlowHandler(BaseHandler):
    """Handler para el flujo de configuración del Grid Bot"""
    
    def handle_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /config"""
        try:
            # Establecer estado de conversación
            bot.set_conversation_state(chat_id, "config_pair_selection", {})
            
            message = "⚙️ <b>CONFIGURACIÓN DEL GRID BOT</b>\n\n"
            message += "Vamos a configurar tu bot paso a paso.\n\n"
            message += "1️⃣ <b>Selecciona el par de trading:</b>\n"
            message += "Envía el nombre del par (ej: ETH/USDT, BTC/USDT)\n\n"
            message += "📋 <b>Pares soportados:</b>\n"
            
            pairs = self.get_supported_pairs()
            for i, pair in enumerate(pairs, 1):
                message += f"{i}. {pair}\n"
            
            message += "\n💡 <i>Escribe el par exactamente como aparece en la lista</i>"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "iniciando configuración", e)
    
    def handle_pair_selection(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la selección de par durante la configuración"""
        try:
            pair = message_text.strip().upper()
            supported_pairs = self.get_supported_pairs()
            
            if pair not in supported_pairs:
                message = f"❌ Par no soportado: {pair}\n\n"
                message += "📋 <b>Pares disponibles:</b>\n"
                for p in supported_pairs:
                    message += f"• {p}\n"
                message += "\n💡 <i>Escribe el par exactamente como aparece</i>"
                bot.send_message(chat_id, message)
                return
            
            # Guardar par seleccionado en el estado
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            state['data']['pair'] = pair
            
            # Cambiar a siguiente paso
            bot.set_conversation_state(chat_id, "config_capital_input", state['data'])
            
            message = f"✅ <b>Par seleccionado:</b> {pair}\n\n"
            message += "2️⃣ <b>Ingresa tu capital total (en USDT):</b>\n\n"
            message += "💡 <i>Ejemplos:</i>\n"
            message += "• Para $50 USDT, escribe: <code>50</code>\n"
            message += "• Para $100.5 USDT, escribe: <code>100.5</code>\n\n"
            message += "ℹ️ <i>El bot calculará automáticamente la configuración óptima</i>"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "selección de par", e)
    
    def handle_capital_input(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el input del capital durante la configuración"""
        try:
            # Validar y convertir capital
            capital_str = message_text.strip().replace(',', '.')
            capital = float(capital_str)
            
            if capital < 10:
                bot.send_message(chat_id, "❌ El capital mínimo es $10 USDT. Intenta de nuevo:")
                return
            
            if capital > 10000:
                bot.send_message(
                    chat_id, 
                    "⚠️ Capital muy alto. ¿Estás seguro? Para confirmar escribe 'sí', o ingresa un valor menor:"
                )
                # Guardar capital pendiente
                state = bot.get_conversation_state(chat_id)
                if state is None:
                    bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                    return
                state['data']['pending_capital'] = capital
                return
            
            # Procesar capital válido
            self._process_valid_capital(chat_id, capital, bot)
            
        except ValueError:
            bot.send_message(chat_id, "❌ Formato inválido. Ingresa solo números (ej: 50 o 100.5):")
        except Exception as e:
            self.send_error_message(bot, chat_id, "procesando capital", e)
    
    def _process_valid_capital(self, chat_id: str, capital: float, bot: TelegramBot):
        """Procesa capital válido y muestra configuración sugerida"""
        try:
            from services.grid.main import MODO_PRODUCTIVO
            
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
                
            pair = state['data']['pair']
            
            # Calcular configuración óptima
            optimal_config = self.calculate_optimal_config(pair, capital)
            state['data'].update(optimal_config)
            
            # Cambiar a confirmación
            bot.set_conversation_state(chat_id, "config_confirmation", state['data'])
            
            # Crear mensaje diferente según el modo
            if not MODO_PRODUCTIVO:  # Modo Sandbox
                message = f"🟡 <b>MODO SANDBOX ACTIVADO</b>\n\n"
                message += f"💰 <b>Capital automático:</b> $1000 USDT (simulado)\n"
                message += f"ℹ️ Tu solicitud de ${capital} USDT se ignora en sandbox\n\n"
            else:  # Modo Productivo
                capital_minimo = optimal_config.get('capital_minimo_sugerido', 600)
                if capital < capital_minimo:
                    message = f"⚠️ <b>CAPITAL INSUFICIENTE</b>\n\n"
                    message += f"💰 <b>Solicitado:</b> ${capital} USDT\n"
                    message += f"💡 <b>Mínimo requerido:</b> ${capital_minimo} USDT\n"
                    message += f"🎯 <b>Capital ajustado a:</b> ${optimal_config['total_capital']} USDT\n\n"
                    message += f"📈 Para 30 niveles + 10% rango necesitas mínimo ${capital_minimo} USDT\n\n"
                else:
                    message = f"🟢 <b>MODO PRODUCTIVO</b>\n\n"
                    message += f"💰 <b>Capital:</b> ${capital} USDT (dinero real)\n"
                    message += f"⚠️ <b>¡ADVERTENCIA!</b> Operarás con dinero real\n\n"
            
            # Configuración optimizada (misma para ambos modos)
            message += "🎯 <b>Configuración Optimizada (Backtesting):</b>\n"
            message += f"📊 <b>Par:</b> {optimal_config['pair']}\n"
            message += f"🎚️ <b>Niveles:</b> {optimal_config['grid_levels']} (óptimo validado)\n"
            message += f"📈 <b>Rango:</b> ±{optimal_config['price_range_percent']}% (óptimo validado)\n"
            message += f"🛡️ <b>Stop Loss:</b> {optimal_config['stop_loss_percent']}% (activo)\n"
            message += f"🧠 <b>Trailing Up:</b> Desactivado (Cerebro decide)\n\n"
            
            message += "✅ ¿Confirmas esta configuración optimizada?\n\n"
            message += "Responde:\n"
            message += "• <code>sí</code> para confirmar\n"
            message += "• <code>no</code> para cancelar"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "procesando configuración", e)
    
    def handle_config_confirmation(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la confirmación de configuración"""
        try:
            response = message_text.strip().lower()
            state = bot.get_conversation_state(chat_id)
            
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            # Verificar si hay capital pendiente de confirmación
            if 'pending_capital' in state['data'] and response == 'sí':
                capital = state['data']['pending_capital']
                del state['data']['pending_capital']
                self._process_valid_capital(chat_id, capital, bot)
                return
            
            if response in ['sí', 'si', 'yes', 'confirmar']:
                # Guardar configuración
                config_data = state['data']
                
                if self.save_user_config(chat_id, config_data):
                    bot.clear_conversation_state(chat_id)
                    
                    from services.grid.main import obtener_configuracion_trading
                    trading_config = obtener_configuracion_trading()
                    
                    modo_icon = "🟡" if trading_config['modo'] == 'SANDBOX' else "🟢"
                    
                    message = "✅ <b>¡Configuración optimizada guardada!</b>\n\n"
                    message += f"{modo_icon} <b>Modo:</b> {trading_config['modo']}\n"
                    message += f"📊 <b>Resumen de la configuración:</b>\n"
                    message += f"• <b>Par:</b> {config_data['pair']}\n"
                    message += f"• <b>Capital:</b> ${config_data['total_capital']} USDT\n"
                    message += f"• <b>Niveles:</b> {config_data['grid_levels']} (backtesting validado)\n"
                    message += f"• <b>Rango:</b> ±{config_data['price_range_percent']}% (backtesting validado)\n"
                    message += f"• <b>Stop Loss:</b> {config_data['stop_loss_percent']}% ✅\n"
                    message += f"• <b>Trailing Up:</b> Desactivado (Cerebro decide) 🧠\n\n"
                    
                    if trading_config['modo'] == 'SANDBOX':
                        message += "🟡 <b>Modo Sandbox:</b> Operaciones simuladas, sin riesgo\n"
                    else:
                        message += "🟢 <b>Modo Productivo:</b> ⚠️ Operaciones con dinero real\n"
                    
                    message += "\n🚀 Usa /start_bot para iniciar el trading con cerebro integrado"
                    
                    bot.send_message(chat_id, message)
                else:
                    bot.send_message(chat_id, "❌ Error guardando configuración. Intenta de nuevo.")
                    
            elif response in ['no', 'cancelar', 'cancel']:
                bot.clear_conversation_state(chat_id)
                bot.send_message(chat_id, "❌ Configuración cancelada. Usa /config para empezar de nuevo.")
                
            elif response == 'personalizar':
                bot.send_message(
                    chat_id, 
                    "⚙️ Personalización avanzada estará disponible en próximas versiones.\n\n"
                    "¿Confirmas la configuración automática? (sí/no)"
                )
            else:
                bot.send_message(
                    chat_id,
                    "❓ Respuesta no entendida.\n\n"
                    "Responde <code>sí</code> para confirmar o <code>no</code> para cancelar:"
                )
                
        except Exception as e:
            self.send_error_message(bot, chat_id, "confirmación", e) 