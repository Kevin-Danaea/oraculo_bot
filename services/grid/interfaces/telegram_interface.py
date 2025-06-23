"""
Interfaz de Telegram específica para el Grid Trading Bot.
Maneja todos los comandos y lógica de conversación específica del grid bot.
"""
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from shared.database.session import get_db_session
from shared.database.models import GridBotConfig, GridBotState
from shared.services.logging_config import get_logger
from shared.services.telegram_bot_service import TelegramBot
from services.grid.schedulers.grid_scheduler import (
    start_grid_bot_scheduler, 
    stop_grid_bot_scheduler,
    get_grid_scheduler
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
        """Registra todos los comandos específicos del grid bot"""
        self.bot.register_command("start", self.handle_start_command)
        self.bot.register_command("config", self.handle_config_command)
        self.bot.register_command("start_bot", self.handle_start_bot_command)
        self.bot.register_command("stop_bot", self.handle_stop_bot_command)
        self.bot.register_command("restart_bot", self.handle_restart_bot_command)
        self.bot.register_command("status", self.handle_status_command)
        self.bot.register_command("delete_config", self.handle_delete_config_command)
        
        # Handlers para estados de conversación
        self.bot.register_command("config_pair_selection", self.handle_pair_selection)
        self.bot.register_command("config_capital_input", self.handle_capital_input)
        self.bot.register_command("config_confirmation", self.handle_config_confirmation)
        
        logger.info("✅ Comandos del Grid Bot registrados en Telegram")
    
    def get_supported_pairs(self) -> list:
        """Lista de pares soportados"""
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
            'SOL/USDT', 'DOT/USDT', 'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT'
        ]
    
    def calculate_optimal_config(self, pair: str, capital: float) -> Dict[str, Any]:
        """Calcula configuración óptima basada en el capital"""
        if capital < 50:
            grid_levels = 2
            price_range = 5.0
        elif capital < 100:
            grid_levels = 4
            price_range = 8.0
        elif capital < 500:
            grid_levels = 6
            price_range = 10.0
        else:
            grid_levels = 6
            price_range = 12.0
        
        return {
            'pair': pair,
            'total_capital': capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range
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
                
                # Crear nueva configuración
                new_config = GridBotConfig(
                    pair=config_data['pair'],
                    total_capital=config_data['total_capital'],
                    grid_levels=config_data['grid_levels'],
                    price_range_percent=config_data['price_range_percent'],
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
            message += "/delete_config - Borrar configuración\n"
            
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
        """Maneja el comando /start_bot"""
        try:
            # Verificar configuración
            user_config = self.get_user_config(chat_id)
            if not user_config:
                message = "⚠️ <b>No tienes configuración guardada</b>\n\n"
                message += "Usa /config para configurar el bot primero."
                bot.send_message(chat_id, message)
                return
            
            # Verificar si ya está ejecutándose
            scheduler = get_grid_scheduler()
            if scheduler and scheduler.running:
                bot.send_message(chat_id, "⚠️ El bot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            # Iniciar bot
            import threading
            
            def start_bot_async():
                try:
                    start_grid_bot_scheduler()
                    bot.send_message(
                        chat_id, 
                        f"🚀 <b>¡Grid Bot iniciado!</b>\n\n"
                        f"📊 Trading: {user_config.pair}\n"
                        f"💰 Capital: ${user_config.total_capital} USDT\n\n"
                        f"Usa /status para monitorear el progreso."
                    )
                except Exception as e:
                    logger.error(f"❌ Error iniciando bot: {e}")
                    bot.send_message(chat_id, f"❌ Error iniciando bot: {str(e)}")
            
            threading.Thread(target=start_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
        except Exception as e:
            logger.error(f"❌ Error en start_bot: {e}")
            bot.send_message(chat_id, "❌ Error iniciando bot")
    
    def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /stop_bot"""
        try:
            scheduler = get_grid_scheduler()
            if not scheduler or not scheduler.running:
                bot.send_message(chat_id, "ℹ️ El bot ya está detenido.")
                return
            
            import threading
            
            def stop_bot_async():
                try:
                    stop_grid_bot_scheduler()
                    bot.send_message(
                        chat_id, 
                        "🛑 <b>Grid Bot detenido correctamente</b>\n\n"
                        "Todas las órdenes activas han sido canceladas."
                    )
                except Exception as e:
                    logger.error(f"❌ Error deteniendo bot: {e}")
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
        """Maneja el comando /status"""
        try:
            scheduler = get_grid_scheduler()
            is_running = scheduler and scheduler.running
            
            message = "📊 <b>ESTADO DEL GRID BOT</b>\n\n"
            
            if is_running:
                message += "🟢 <b>Estado:</b> Ejecutándose\n"
            else:
                message += "🔴 <b>Estado:</b> Detenido\n"
            
            # Mostrar configuración del usuario
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"\n⚙️ <b>Configuración actual:</b>\n"
                message += f"📈 <b>Par:</b> {user_config.pair}\n"
                message += f"💰 <b>Capital:</b> ${user_config.total_capital} USDT\n"
                message += f"🎚️ <b>Niveles:</b> {user_config.grid_levels}\n"
                message += f"📊 <b>Rango:</b> ±{user_config.price_range_percent}%\n"
                message += f"📅 <b>Creado:</b> {user_config.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                message += "\n⚠️ <b>Sin configuración guardada</b>\n"
                message += "Usa /config para configurar el bot\n"
            
            # Estado del scheduler
            if scheduler:
                jobs = scheduler.get_jobs()
                message += f"\n🔧 <b>Jobs activos:</b> {len(jobs)}\n"
            
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