"""
Interfaz de Telegram específica para el Grid Trading Bot.
Maneja todos los comandos y lógica de conversación específica del grid bot.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from shared.database.session import get_db_session
from shared.database.models import GridBotConfig
from shared.services.logging_config import get_logger
from shared.services.telegram_bot_service import TelegramBot
from services.grid.schedulers.grid_scheduler import (
    start_grid_bot_scheduler, 
    stop_grid_bot_scheduler,
    get_grid_scheduler,
    start_grid_bot_manual,
    stop_grid_bot_manual,
    get_grid_bot_status
)

logger = get_logger(__name__)


class GridTelegramInterface:
    """
    Interfaz de Telegram para el Grid Trading Bot.
    Maneja la lógica específica de comandos y configuración del bot.
    """
    
    def __init__(self, telegram_bot: TelegramBot):
        """
        Inicializa la interfaz con el bot de Telegram
        
        Args:
            telegram_bot: Instancia del bot de Telegram genérico
        """
        self.bot = telegram_bot
        self.register_commands()
    
    def register_commands(self):
        """Registra todos los comandos específicos del grid bot V2"""
        # Comandos básicos V1
        self.bot.register_command("start", self.handle_start_command)
        self.bot.register_command("config", self.handle_config_command)
        self.bot.register_command("start_bot", self.handle_start_bot_command)
        self.bot.register_command("stop_bot", self.handle_stop_bot_command)
        self.bot.register_command("restart_bot", self.handle_restart_bot_command)
        self.bot.register_command("status", self.handle_status_command)
        self.bot.register_command("delete_config", self.handle_delete_config_command)
        
        # Comandos V2: Estrategias Avanzadas
        self.bot.register_command("enable_stop_loss", self.handle_enable_stop_loss_command)
        self.bot.register_command("disable_stop_loss", self.handle_disable_stop_loss_command)
        self.bot.register_command("enable_trailing", self.handle_enable_trailing_command)
        self.bot.register_command("disable_trailing", self.handle_disable_trailing_command)
        self.bot.register_command("set_stop_loss", self.handle_set_stop_loss_command)
        self.bot.register_command("protections", self.handle_protections_command)
        
        # Handlers para estados de conversación
        self.bot.register_command("config_pair_selection", self.handle_pair_selection)
        self.bot.register_command("config_capital_input", self.handle_capital_input)
        self.bot.register_command("config_confirmation", self.handle_config_confirmation)
        
        logger.info("✅ Comandos del Grid Bot V2 registrados en Telegram")
    
    def get_supported_pairs(self) -> list:
        """Lista de pares soportados"""
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
            'SOL/USDT', 'DOT/USDT', 'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT'
        ]
    
    def calculate_optimal_config(self, pair: str, capital: float) -> Dict[str, Any]:
        """Calcula configuración óptima basada en el capital - V2 con estrategias avanzadas"""
        if capital < 50:
            grid_levels = 2
            price_range = 5.0
            stop_loss = 3.0  # Más conservador para capitales pequeños
        elif capital < 100:
            grid_levels = 4
            price_range = 8.0
            stop_loss = 4.0
        elif capital < 500:
            grid_levels = 6
            price_range = 10.0
            stop_loss = 5.0
        else:
            grid_levels = 6
            price_range = 12.0
            stop_loss = 6.0  # Más agresivo para capitales grandes
        
        return {
            'pair': pair,
            'total_capital': capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range,
            'stop_loss_percent': stop_loss,
            'enable_stop_loss': True,  # Siempre activado por defecto
            'enable_trailing_up': True  # Siempre activado por defecto
        }
    
    def get_user_config(self, chat_id: str) -> Optional[GridBotConfig]:
        """Obtiene la configuración activa del usuario"""
        try:
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).first()
                return config
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración del usuario: {e}")
            return None
    
    def save_user_config(self, chat_id: str, config_data: Dict[str, Any]) -> bool:
        """Guarda la configuración del usuario en la base de datos"""
        try:
            with get_db_session() as db:
                # Desactivar configuraciones anteriores
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id
                ).update({'is_active': False})
                
                # Crear nueva configuración V2
                new_config = GridBotConfig(
                    pair=config_data['pair'],
                    total_capital=config_data['total_capital'],
                    grid_levels=config_data['grid_levels'],
                    price_range_percent=config_data['price_range_percent'],
                    stop_loss_percent=config_data.get('stop_loss_percent', 5.0),
                    enable_stop_loss=config_data.get('enable_stop_loss', True),
                    enable_trailing_up=config_data.get('enable_trailing_up', True),
                    telegram_chat_id=chat_id,
                    is_active=True
                )
                
                db.add(new_config)
                db.commit()
                
                logger.info(f"✅ Configuración guardada para usuario {chat_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error guardando configuración: {e}")
            return False
    
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
            logger.error(f"❌ Error en comando start: {e}")
            bot.send_message(chat_id, "❌ Error procesando comando start")
    
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
            logger.error(f"❌ Error en comando config: {e}")
            bot.send_message(chat_id, "❌ Error iniciando configuración")
    
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
            logger.error(f"❌ Error en selección de par: {e}")
            bot.send_message(chat_id, "❌ Error procesando par. Intenta de nuevo.")
    
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
            logger.error(f"❌ Error procesando capital: {e}")
            bot.send_message(chat_id, "❌ Error procesando capital. Intenta de nuevo:")
    
    def _process_valid_capital(self, chat_id: str, capital: float, bot: TelegramBot):
        """Procesa capital válido y muestra configuración sugerida"""
        try:
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
            
            # Mostrar configuración sugerida
            message = f"💰 <b>Capital:</b> ${capital} USDT\n\n"
            message += "🎯 <b>Configuración automática sugerida:</b>\n"
            message += f"📊 <b>Par:</b> {optimal_config['pair']}\n"
            message += f"🎚️ <b>Niveles de grid:</b> {optimal_config['grid_levels']}\n"
            message += f"📈 <b>Rango de precios:</b> ±{optimal_config['price_range_percent']}%\n\n"
            message += "✅ ¿Confirmas esta configuración?\n\n"
            message += "Responde:\n"
            message += "• <code>sí</code> para confirmar\n"
            message += "• <code>no</code> para cancelar\n"
            message += "• <code>personalizar</code> para configuración avanzada"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error procesando configuración: {e}")
            bot.send_message(chat_id, "❌ Error generando configuración")
    
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
                    
                    message = "✅ <b>¡Configuración guardada correctamente!</b>\n\n"
                    message += f"📊 <b>Resumen:</b>\n"
                    message += f"• <b>Par:</b> {config_data['pair']}\n"
                    message += f"• <b>Capital:</b> ${config_data['total_capital']} USDT\n"
                    message += f"• <b>Niveles:</b> {config_data['grid_levels']}\n"
                    message += f"• <b>Rango:</b> ±{config_data['price_range_percent']}%\n\n"
                    message += "🚀 Usa /start_bot para iniciar el trading"
                    
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
            logger.error(f"❌ Error en confirmación: {e}")
            bot.send_message(chat_id, "❌ Error procesando confirmación")
    
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
            import threading
            
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
                    logger.error(f"❌ Error en start_bot_async: {e}")
                    bot.send_message(chat_id, f"❌ Error iniciando bot: {str(e)}")
            
            threading.Thread(target=start_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
        except Exception as e:
            logger.error(f"❌ Error en start_bot: {e}")
            bot.send_message(chat_id, "❌ Error iniciando bot")
    
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
            
            import threading
            
            def stop_bot_async():
                try:
                    success, result_message = stop_grid_bot_manual()
                    
                    if success:
                        message = "🛑 <b>Grid Bot detenido correctamente</b>\n\n"
                        message += "✅ Todas las órdenes activas han sido canceladas\n"
                        message += "⏸️ Bot en modo standby\n\n"
                        message += "▶️ Usa /start_bot para reanudar trading"
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ <b>Error deteniendo bot:</b> {result_message}")
                        
                except Exception as e:
                    logger.error(f"❌ Error en stop_bot_async: {e}")
                    bot.send_message(chat_id, f"❌ Error deteniendo bot: {str(e)}")
            
            threading.Thread(target=stop_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Deteniendo Grid Bot...")
            
        except Exception as e:
            logger.error(f"❌ Error en stop_bot: {e}")
            bot.send_message(chat_id, "❌ Error deteniendo bot")
    
    def handle_restart_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /restart_bot"""
        try:
            import threading
            import time
            
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
                    logger.error(f"❌ Error reiniciando bot: {e}")
                    bot.send_message(chat_id, f"❌ Error reiniciando bot: {str(e)}")
            
            threading.Thread(target=restart_bot_async, daemon=True).start()
            bot.send_message(chat_id, "🔄 Reiniciando Grid Bot...")
            
        except Exception as e:
            logger.error(f"❌ Error en restart_bot: {e}")
            bot.send_message(chat_id, "❌ Error reiniciando bot")
    
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
            logger.error(f"❌ Error en status: {e}")
            bot.send_message(chat_id, "❌ Error obteniendo estado")
    
    def handle_delete_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /delete_config"""
        try:
            user_config = self.get_user_config(chat_id)
            
            if not user_config:
                bot.send_message(chat_id, "ℹ️ No tienes configuración guardada.")
                return
            
            # Desactivar configuración en la base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({'is_active': False})
                db.commit()
            
            bot.send_message(
                chat_id, 
                f"✅ Configuración eliminada correctamente.\n\n"
                f"Se eliminó: {user_config.pair} con ${user_config.total_capital} USDT"
            )
            
        except Exception as e:
            logger.error(f"❌ Error eliminando config: {e}")
            bot.send_message(chat_id, "❌ Error eliminando configuración")

    # ============================================================================
    # COMANDOS V2 - ESTRATEGIAS AVANZADAS
    # ============================================================================

    def handle_enable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /enable_stop_loss"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            # Actualizar en base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({'enable_stop_loss': True})
                db.commit()
            
            message = "🛡️ <b>STOP-LOSS ACTIVADO</b>\n\n"
            message += f"📉 Se activará si el precio baja {user_config.stop_loss_percent}% debajo del nivel más bajo\n"
            message += f"⚠️ El bot se detendrá automáticamente si se activa\n\n"
            message += f"💡 Usa /set_stop_loss X para cambiar el porcentaje"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error habilitando stop-loss: {e}")
            bot.send_message(chat_id, "❌ Error activando stop-loss")

    def handle_disable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /disable_stop_loss"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            # Actualizar en base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({'enable_stop_loss': False})
                db.commit()
            
            message = "🚫 <b>STOP-LOSS DESACTIVADO</b>\n\n"
            message += f"⚠️ <b>ATENCIÓN:</b> El bot NO se protegerá contra caídas bruscas\n"
            message += f"💡 Usa /enable_stop_loss para reactivar la protección"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error deshabilitando stop-loss: {e}")
            bot.send_message(chat_id, "❌ Error desactivando stop-loss")

    def handle_enable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /enable_trailing"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            # Actualizar en base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({'enable_trailing_up': True})
                db.commit()
            
            message = "📈 <b>TRAILING UP ACTIVADO</b>\n\n"
            message += f"🚀 El bot seguirá tendencias alcistas automáticamente\n"
            message += f"🎯 Reposicionará el grid si el precio rompe el límite superior\n\n"
            message += f"💡 Esto mantiene al bot activo en mercados alcistas"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error habilitando trailing up: {e}")
            bot.send_message(chat_id, "❌ Error activando trailing up")

    def handle_disable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /disable_trailing"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            # Actualizar en base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({'enable_trailing_up': False})
                db.commit()
            
            message = "🚫 <b>TRAILING UP DESACTIVADO</b>\n\n"
            message += f"📊 El bot mantendrá su grid fijo sin reposicionarse\n"
            message += f"⚠️ Puede quedarse fuera del mercado en tendencias alcistas\n\n"
            message += f"💡 Usa /enable_trailing para reactivar"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error deshabilitando trailing up: {e}")
            bot.send_message(chat_id, "❌ Error desactivando trailing up")

    def handle_set_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /set_stop_loss X"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            # Extraer porcentaje del mensaje
            parts = message_text.strip().split()
            if len(parts) != 2:
                bot.send_message(
                    chat_id, 
                    "❌ Formato incorrecto.\n\n"
                    "✅ Uso correcto: <code>/set_stop_loss 3.5</code>\n"
                    "💡 Ejemplo: 3.5 significa 3.5% de pérdida máxima"
                )
                return
            
            try:
                new_percentage = float(parts[1])
                if new_percentage < 0.1 or new_percentage > 20:
                    bot.send_message(
                        chat_id,
                        "❌ El porcentaje debe estar entre 0.1% y 20%\n\n"
                        "💡 Valores recomendados:\n"
                        "• Conservador: 2-3%\n"
                        "• Moderado: 4-6%\n"
                        "• Agresivo: 7-10%"
                    )
                    return
            except ValueError:
                bot.send_message(chat_id, "❌ Porcentaje inválido. Usa números como: 3.5")
                return
            
            # Actualizar en base de datos
            with get_db_session() as db:
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).update({
                    'stop_loss_percent': new_percentage,
                    'enable_stop_loss': True  # Activar automáticamente al configurar
                })
                db.commit()
            
            message = f"✅ <b>STOP-LOSS CONFIGURADO</b>\n\n"
            message += f"📉 <b>Nuevo porcentaje:</b> {new_percentage}%\n"
            message += f"🛡️ <b>Estado:</b> Activado automáticamente\n\n"
            message += f"💡 El bot se detendrá si el precio baja {new_percentage}% debajo del nivel más bajo"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error configurando stop-loss: {e}")
            bot.send_message(chat_id, "❌ Error configurando stop-loss")

    def handle_protections_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /protections"""
        try:
            user_config = self.get_user_config(chat_id)
            if not user_config:
                bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
                return
            
            message = "🛡️ <b>ESTADO DE PROTECCIONES V2</b>\n\n"
            
            # Stop-Loss
            if bool(user_config.enable_stop_loss):
                message += f"🟢 <b>Stop-Loss:</b> ACTIVO ({user_config.stop_loss_percent}%)\n"
                message += f"   📉 Se activará si baja {user_config.stop_loss_percent}% del nivel más bajo\n\n"
            else:
                message += f"🔴 <b>Stop-Loss:</b> INACTIVO\n"
                message += f"   ⚠️ Sin protección contra caídas bruscas\n\n"
            
            # Trailing Up
            if bool(user_config.enable_trailing_up):
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
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error mostrando protecciones: {e}")
            bot.send_message(chat_id, "❌ Error obteniendo estado de protecciones")


def get_dynamic_grid_config(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración dinámica para el grid bot desde la base de datos.
    Esta función reemplaza la configuración hardcodeada en grid_scheduler.
    """
    try:
        with get_db_session() as db:
            config = None
            
            # Buscar configuración específica del usuario si se proporciona chat_id
            if chat_id:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                ).first()
            
            # Si no se encuentra configuración específica, buscar cualquier configuración activa
            if not config:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.is_active == True
                ).first()
            
            if config:
                logger.info(f"✅ Usando configuración dinámica: {config.pair}")
                return config.to_dict()
            else:
                # Configuración por defecto como fallback
                logger.warning("⚠️ No hay configuración dinámica, usando valores por defecto")
                return {
                    'pair': 'ETH/USDT',
                    'total_capital': 56.88,
                    'grid_levels': 4,
                    'price_range_percent': 10.0
                }
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración dinámica: {e}")
        # Fallback a configuración por defecto
        return {
            'pair': 'ETH/USDT',
            'total_capital': 56.88,
            'grid_levels': 4,
            'price_range_percent': 10.0
        } 