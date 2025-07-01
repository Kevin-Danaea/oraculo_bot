"""
Handler para el flujo de configuración del Grid Bot.
Maneja el proceso paso a paso de configuración: selección de par, capital, confirmación.
"""
from shared.services.telegram_bot_service import TelegramBot
from .base_handler import BaseHandler
from services.grid.core.trading_mode_manager import trading_mode_manager


class ConfigFlowHandler(BaseHandler):
    """Handler para el flujo de configuración del Grid Bot"""
    
    def handle_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /config - Muestra configuraciones actuales y permite modificar capital"""
        try:
            # Limpiar estados de conversación previos
            bot.clear_conversation_state(chat_id)
            
            # Obtener configuraciones actuales del usuario
            configs = {}
            for config_type in ['ETH', 'BTC', 'AVAX']:
                config = self.get_user_config_by_type(chat_id, config_type)
                if config and getattr(config, 'is_configured', False):
                    configs[config_type] = {
                        'capital': config.total_capital,
                        'is_configured': True
                    }
                else:
                    configs[config_type] = {
                        'capital': 0,
                        'is_configured': False
                    }
            
            # Mostrar estado actual de configuraciones
            message = "📊 <b>CONFIGURACIONES MULTIBOT</b>\n\n"
            message += "🎯 <b>Estado actual de tus configuraciones:</b>\n\n"
            
            pair_names = {'ETH': 'ETH/USDT', 'BTC': 'BTC/USDT', 'AVAX': 'AVAX/USDT'}
            
            for i, (config_type, pair_name) in enumerate(pair_names.items(), 1):
                config_info = configs[config_type]
                if config_info['is_configured']:
                    status_icon = "🟢"
                    status_text = f"${config_info['capital']} USDT"
                else:
                    status_icon = "⚪"
                    status_text = "Sin configurar"
                
                message += f"{i}. {status_icon} <b>{config_type}</b> ({pair_name})\n"
                message += f"   💰 Capital: {status_text}\n\n"
            
            message += "💡 <b>¿Qué par quieres configurar?</b>\n"
            message += "Responde con el número (1-3) o el nombre del par:\n"
            message += "• <code>1</code> o <code>ETH</code> para ETH/USDT\n"
            message += "• <code>2</code> o <code>BTC</code> para BTC/USDT\n"
            message += "• <code>3</code> o <code>AVAX</code> para AVAX/USDT\n\n"
            message += "📋 <b>Nota:</b> Solo se puede modificar el capital.\n"
            message += "Los demás parámetros están optimizados por backtesting."
            
            # Inicializar estado de configuración
            config_data = {
                'config_type': '',
                'total_capital': 0.0
            }
            bot.set_conversation_state(chat_id, "config_type_selection", config_data)
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "config", e)
    
    def handle_config_type_selection(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja la selección del par a configurar (ETH, BTC, AVAX)"""
        try:
            state = bot.get_conversation_state(chat_id)
            if state is None:
                bot.send_message(chat_id, "❌ Error: Estado de conversación perdido. Usa /config para empezar de nuevo.")
                return
            
            # Mapeo de números y nombres a tipos de configuración
            config_mapping = {
                '1': 'ETH', 'ETH': 'ETH',
                '2': 'BTC', 'BTC': 'BTC', 
                '3': 'AVAX', 'AVAX': 'AVAX'
            }
            
            # Normalizar entrada del usuario
            user_input = message_text.strip().upper()
            selected_type = config_mapping.get(user_input)
            
            if not selected_type:
                bot.send_message(
                    chat_id,
                    "❌ Opción no válida.\n\n"
                    "💡 Opciones disponibles:\n"
                    "• <code>1</code> o <code>ETH</code> para ETH/USDT\n"
                    "• <code>2</code> o <code>BTC</code> para BTC/USDT\n"
                    "• <code>3</code> o <code>AVAX</code> para AVAX/USDT"
                )
                return
            
            # Obtener información de la configuración existente
            existing_config = self.get_user_config_by_type(chat_id, selected_type)
            pair_name = {'ETH': 'ETH/USDT', 'BTC': 'BTC/USDT', 'AVAX': 'AVAX/USDT'}[selected_type]
            
            # Guardar tipo seleccionado
            state['data']['config_type'] = selected_type
            
            # Cambiar a entrada de capital
            bot.set_conversation_state(chat_id, "config_capital_input", state['data'])
            
            # Mostrar información específica del par
            is_productive = trading_mode_manager.is_productive()
            
            if not is_productive:  # Modo Sandbox
                message = f"🟡 <b>CONFIGURANDO {selected_type} (MODO SANDBOX)</b>\n\n"
                message += f"📊 <b>Par:</b> {pair_name}\n"
                message += f"💰 <b>Capital actual:</b> $1000 USDT (fijo para sandbox)\n\n"
                message += "💡 <b>En modo sandbox, el capital es fijo.</b>\n"
                message += "Escribe cualquier número para continuar:"
            else:  # Modo Productivo
                capital_minimo = 30 * 10  # 300 USDT mínimo
                
                if existing_config and getattr(existing_config, 'is_configured', False):
                    current_capital = existing_config.total_capital
                    message = f"🟢 <b>MODIFICANDO {selected_type}</b>\n\n"
                    message += f"📊 <b>Par:</b> {pair_name}\n"
                    message += f"💰 <b>Capital actual:</b> ${current_capital} USDT\n\n"
                    message += "💡 <b>Escribe el nuevo capital en USDT:</b>\n"
                    message += f"• Mínimo recomendado: ${capital_minimo} USDT\n"
                    message += f"• Para 30 niveles ($10 USDT por orden)\n"
                    message += f"• ⚠️ Trading con dinero real"
                else:
                    message = f"🟢 <b>CONFIGURANDO {selected_type}</b>\n\n"
                    message += f"📊 <b>Par:</b> {pair_name}\n"
                    message += f"💰 <b>Capital actual:</b> Sin configurar\n\n"
                    message += "💡 <b>Escribe el capital en USDT:</b>\n"
                    message += f"• Mínimo recomendado: ${capital_minimo} USDT\n"
                    message += f"• Para 30 niveles ($10 USDT por orden)\n"
                    message += f"• ⚠️ Trading con dinero real"
            
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
            
            # Obtener información del par
            config_type = state['data']['config_type']
            pair_name = {'ETH': 'ETH/USDT', 'BTC': 'BTC/USDT', 'AVAX': 'AVAX/USDT'}[config_type]
            
            # Mostrar configuración final
            is_productive = trading_mode_manager.is_productive()
            
            if not is_productive:  # Modo Sandbox
                message = f"🟡 <b>CONFIGURACIÓN SANDBOX - {config_type}</b>\n\n"
                message += f"📊 <b>Par:</b> {pair_name}\n"
                message += f"💰 <b>Capital:</b> $1000 USDT (fijo para sandbox)\n"
                message += f"ℹ️ Tu solicitud de ${capital} USDT se ignora\n\n"
            else:  # Modo Productivo
                capital_minimo = 30 * 10  # 300 USDT mínimo
                
                if capital < capital_minimo:
                    message = f"⚠️ <b>CAPITAL INSUFICIENTE - AJUSTE AUTOMÁTICO</b>\n\n"
                    message += f"📊 <b>Par:</b> {pair_name}\n"
                    message += f"💰 <b>Solicitado:</b> ${capital} USDT\n"
                    message += f"💡 <b>Mínimo requerido:</b> ${capital_minimo} USDT\n"
                    message += f"🎯 <b>Capital ajustado a:</b> ${capital_minimo} USDT\n\n"
                    # Ajustar capital automáticamente
                    state['data']['total_capital'] = capital_minimo
                else:
                    message = f"🟢 <b>CONFIGURACIÓN PRODUCTIVA - {config_type}</b>\n\n"
                    message += f"📊 <b>Par:</b> {pair_name}\n"
                    message += f"💰 <b>Capital:</b> ${capital} USDT\n"
                    message += f"⚠️ <b>¡ADVERTENCIA!</b> Operarás con dinero real\n\n"
            
            # Parámetros técnicos fijos (optimizados por backtesting)
            message += "🎯 <b>Parámetros Técnicos (FIJOS):</b>\n"
            message += f"• <b>Niveles de grid:</b> 30 (optimizado)\n"
            message += f"• <b>Rango de precios:</b> 10% (optimizado)\n"
            message += f"• <b>Stop Loss:</b> 5% (activo)\n"
            message += f"• <b>Trailing Up:</b> ✅ Activo\n\n"
            
            message += "✅ <b>¿Confirmar esta configuración?</b>\n"
            message += "Responde <code>SI</code> para confirmar o <code>NO</code> para cancelar."
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "configurando capital", e)
    
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
                config_type = state['data']['config_type']
                capital = state['data']['total_capital']
                config_data = self.calculate_optimal_config(f"{config_type}/USDT", capital)
                
                # Guardar configuración
                if self.save_user_config(chat_id, config_data):
                    bot.clear_conversation_state(chat_id)
                    
                    trading_config = trading_mode_manager.get_config()
                    
                    modo_icon = "🟡" if trading_config['modo'] == 'SANDBOX' else "🟢"
                    
                    message = "✅ <b>¡Configuración optimizada guardada!</b>\n\n"
                    message += f"{modo_icon} <b>Modo:</b> {trading_config['modo']}\n"
                    message += f"📊 <b>Resumen de la configuración:</b>\n"
                    message += f"• <b>Tipo:</b> {config_type}\n"
                    message += f"• <b>Capital:</b> ${capital} USDT\n"
                    message += f"• <b>Niveles:</b> {config_data['grid_levels']} (fijo, optimizado)\n"
                    message += f"• <b>Rango:</b> ±{config_data['price_range_percent']}% (fijo, optimizado)\n"
                    message += f"• <b>Stop Loss:</b> {config_data['stop_loss_percent']}% ✅\n"
                    message += f"• <b>Trailing Up:</b> ✅ Activo (Optimiza ganancias) 🧠\n\n"
                    
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