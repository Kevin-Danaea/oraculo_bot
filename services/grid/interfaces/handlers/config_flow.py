"""
Handler para el flujo de configuración del Grid Bot.
Maneja el proceso paso a paso de configuración: selección de par, capital, confirmación.
"""
from shared.services.telegram_bot_service import TelegramBot
from .base_handler import BaseHandler


class ConfigFlowHandler(BaseHandler):
    """Handler para el flujo de configuración del Grid Bot"""
    
    def handle_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /config - Inicia el flujo de configuración simplificado"""
        try:
            # Limpiar estados de conversación previos
            bot.clear_conversation_state(chat_id)
            
            # Inicializar estado de configuración
            config_data = {
                'pair': '',
                'total_capital': 0.0
            }
            
            # Cambiar a selección de par
            bot.set_conversation_state(chat_id, "config_pair_selection", config_data)
            
            # Mostrar pares disponibles (por ahora solo ETH/USDT)
            supported_pairs = self.get_supported_pairs()
            message = "🎯 <b>CONFIGURACIÓN DEL GRID BOT v3.0</b>\n\n"
            message += "📊 <b>Paso 1: Selecciona el par de trading</b>\n\n"
            message += "🪙 <b>Pares disponibles:</b>\n"
            
            for i, pair in enumerate(supported_pairs, 1):
                message += f"{i}. <code>{pair}</code>\n"
            
            message += "\n⚠️ <b>Nota:</b> Por ahora solo ETH/USDT está disponible.\n"
            message += "🔄 En futuras versiones agregaremos más pares.\n\n"
            message += "💡 <b>Responde con el número del par:</b>\n"
            message += "Ejemplo: <code>1</code> para {supported_pairs[0]}"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "config", e)
    
    def handle_pair_selection(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la selección del par de trading"""
        try:
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            # Obtener lista de pares soportados
            supported_pairs = self.get_supported_pairs()
            
            # Intentar parsear como número
            try:
                pair_index = int(message_text.strip()) - 1  # Convertir a índice base 0
                
                if pair_index < 0 or pair_index >= len(supported_pairs):
                    bot.send_message(
                        chat_id,
                        f"❌ Número inválido. Debe ser entre 1 y {len(supported_pairs)}.\n\n"
                        f"Pares disponibles:\n" + 
                        "\n".join([f"{i}. {pair}" for i, pair in enumerate(supported_pairs, 1)])
                    )
                    return
                
                selected_pair = supported_pairs[pair_index]
                
            except ValueError:
                # Si no es un número, intentar buscar por nombre
                selected_pair = message_text.strip().upper()
                if selected_pair not in supported_pairs:
                    bot.send_message(
                        chat_id,
                        f"❌ Par no válido: {message_text}\n\n"
                        f"Pares disponibles:\n" + 
                        "\n".join([f"{i}. {pair}" for i, pair in enumerate(supported_pairs, 1)]) +
                        f"\n\n💡 Responde con el número (1-{len(supported_pairs)}) o el nombre exacto del par."
                    )
                    return
            
            # Guardar par seleccionado
            state['data']['pair'] = selected_pair
            
            # Cambiar a entrada de capital
            bot.set_conversation_state(chat_id, "config_capital_input", state['data'])
            
            # Mostrar siguiente paso
            from services.grid.main import MODO_PRODUCTIVO
            
            if not MODO_PRODUCTIVO:  # Modo Sandbox
                message = f"✅ <b>Par seleccionado:</b> {selected_pair}\n\n"
                message += "💰 <b>Paso 2: Capital para trading</b>\n\n"
                message += "🟡 <b>MODO SANDBOX ACTIVO</b>\n"
                message += "• Capital fijo: $1000 USDT (simulado)\n"
                message += "• Sin riesgo, para pruebas\n\n"
                message += "💡 <b>Escribe cualquier número (se ignorará):</b>\n"
                message += "Ejemplo: <code>500</code> o <code>1000</code>"
            else:  # Modo Productivo
                capital_minimo = 30 * 25  # 750 USDT mínimo para 30 niveles con comisiones
                message = f"✅ <b>Par seleccionado:</b> {selected_pair}\n\n"
                message += "💰 <b>Paso 2: Capital para trading</b>\n\n"
                message += "🟢 <b>MODO PRODUCTIVO</b>\n"
                message += f"• Capital mínimo requerido: ${capital_minimo} USDT\n"
                message += f"• Para 30 niveles + 10% rango optimizado\n"
                message += "• ⚠️ Trading con dinero real\n\n"
                message += "💡 <b>Escribe el capital en USDT:</b>\n"
                message += f"Ejemplo: <code>{capital_minimo}</code> o más"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "seleccionando par", e)
    
    def handle_capital_input(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la entrada del capital durante la configuración"""
        try:
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            # Parsear capital
            try:
                capital = float(message_text.strip())
                if capital <= 0:
                    bot.send_message(chat_id, "❌ El capital debe ser mayor a 0. Intenta de nuevo.")
                    return
            except ValueError:
                bot.send_message(
                    chat_id, 
                    "❌ Capital inválido. Escribe un número válido.\n\n"
                    "💡 Ejemplos: <code>500</code>, <code>1000.5</code>"
                )
                return
            
            # Guardar capital en el estado
            state['data']['total_capital'] = capital
            
            # Cambiar a confirmación
            bot.set_conversation_state(chat_id, "config_confirmation", state['data'])
            
            # Calcular configuración óptima
            pair = state['data']['pair']
            optimal_config = self.calculate_optimal_config(pair, capital)
            
            # Mostrar configuración final con parámetros fijos
            from services.grid.main import MODO_PRODUCTIVO
            
            if not MODO_PRODUCTIVO:  # Modo Sandbox
                message = f"🟡 <b>MODO SANDBOX - CONFIGURACIÓN FINAL</b>\n\n"
                message += f"📊 <b>Par seleccionado:</b> {pair}\n"
                message += f"💰 <b>Capital:</b> $1000 USDT (fijo para sandbox)\n"
                message += f"ℹ️ Tu solicitud de ${capital} USDT se ignora\n\n"
            else:  # Modo Productivo
                capital_minimo = optimal_config.get('capital_minimo_sugerido', 750)
                if capital < capital_minimo:
                    message = f"⚠️ <b>CAPITAL INSUFICIENTE - AJUSTE AUTOMÁTICO</b>\n\n"
                    message += f"📊 <b>Par seleccionado:</b> {pair}\n"
                    message += f"💰 <b>Solicitado:</b> ${capital} USDT\n"
                    message += f"💡 <b>Mínimo requerido:</b> ${capital_minimo} USDT\n"
                    message += f"🎯 <b>Capital ajustado a:</b> ${optimal_config['total_capital']} USDT\n\n"
                else:
                    message = f"🟢 <b>MODO PRODUCTIVO - CONFIGURACIÓN FINAL</b>\n\n"
                    message += f"📊 <b>Par seleccionado:</b> {pair}\n"
                    message += f"💰 <b>Capital:</b> ${capital} USDT (dinero real)\n"
                    message += f"⚠️ <b>¡ADVERTENCIA!</b> Operarás con dinero real\n\n"
            
            # Parámetros técnicos fijos (mismos para ambos modos)
            message += "🎯 <b>Parámetros Técnicos (FIJOS):</b>\n"
            message += f"• <b>Niveles de grid:</b> 30 (optimizado por backtesting)\n"
            message += f"• <b>Rango de precios:</b> 10% (optimizado por backtesting)\n"
            message += f"• <b>Stop Loss:</b> {optimal_config['stop_loss_percent']}% (activo)\n"
            message += f"• <b>Trailing Up:</b> Desactivado (Cerebro decide)\n\n"
            
            message += "🧠 <b>Integración con Cerebro:</b>\n"
            message += "• El cerebro decide cuándo operar (ADX + Volatilidad)\n"
            message += "• Futuramente: cerebro elegirá niveles y rangos dinámicamente\n\n"
            
            message += "✅ ¿Confirmas esta configuración optimizada?\n\n"
            message += "Responde:\n"
            message += "• <code>sí</code> para confirmar\n"
            message += "• <code>no</code> para cancelar"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "procesando capital", e)
    
    def handle_config_confirmation(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la confirmación de la configuración"""
        try:
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            response = message_text.strip().lower()
            
            if response in ['sí', 'si', 'yes', 'confirmar']:
                # Calcular configuración óptima final
                pair = state['data']['pair']
                capital = state['data']['total_capital']
                config_data = self.calculate_optimal_config(pair, capital)
                
                # Guardar configuración
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
                    message += f"• <b>Niveles:</b> {config_data['grid_levels']} (fijo, optimizado)\n"
                    message += f"• <b>Rango:</b> ±{config_data['price_range_percent']}% (fijo, optimizado)\n"
                    message += f"• <b>Stop Loss:</b> {config_data['stop_loss_percent']}% ✅\n"
                    message += f"• <b>Trailing Up:</b> Desactivado (Cerebro decide) 🧠\n\n"
                    
                    if trading_config['modo'] == 'SANDBOX':
                        message += "🟡 <b>Modo Sandbox:</b> Operaciones simuladas, sin riesgo\n"
                    else:
                        message += "🟢 <b>Modo Productivo:</b> ⚠️ Operaciones con dinero real\n"
                    
                    message += "\n🧠 <b>Integración con Cerebro:</b>\n"
                    message += "• El cerebro decide cuándo operar automáticamente\n"
                    message += "• Futuramente: cerebro elegirá parámetros dinámicamente\n\n"
                    
                    message += "🚀 Usa /start_bot para iniciar el trading inteligente"
                    
                    bot.send_message(chat_id, message)
                else:
                    bot.send_message(chat_id, "❌ Error guardando configuración. Intenta de nuevo.")
                    
            elif response in ['no', 'cancelar', 'cancel']:
                bot.clear_conversation_state(chat_id)
                bot.send_message(chat_id, "❌ Configuración cancelada. Usa /config para empezar de nuevo.")
            else:
                bot.send_message(
                    chat_id,
                    "❓ Respuesta no entendida.\n\n"
                    "Responde <code>sí</code> para confirmar o <code>no</code> para cancelar:"
                )
                
        except Exception as e:
            self.send_error_message(bot, chat_id, "confirmando configuración", e) 