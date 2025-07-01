"""
Módulo genérico para el servicio de Telegram V2
Basado en python-telegram-bot, asíncrono y modular.
"""
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, cast
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)
from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """
    Clase genérica para un bot de Telegram.
    Maneja el ciclo de vida, registro de comandos y estados de conversación.
    """
    
    def __init__(self):
        """Inicializa el bot de Telegram."""
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("Token de Telegram no configurado")
        
        # Crear aplicación con el nuevo ApplicationBuilder
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self.conversation_states: Dict[str, Dict] = {}  # Almacena estados de conversación
        
        # Registrar manejador genérico para mensajes de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))

    def register_command(self, command: str, handler: Callable):
        """
        Registra un nuevo comando y su manejador.
        
        Args:
            command: Nombre del comando (ej: 'start')
            handler: Función que manejará el comando
        """
        self.application.add_handler(CommandHandler(command, self._command_wrapper(handler)))
        logger.info(f"✅ Comando /{command} registrado")
    
    async def send_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje a un chat específico.
        
        Args:
            chat_id: ID del chat
            message: Mensaje a enviar
            parse_mode: 'HTML' o 'Markdown'
            
        Returns:
            True si el mensaje se envió correctamente
        """
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"✅ Mensaje enviado a Telegram correctamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
            return False

    def _get_conversation_state_key(self, chat_id: str) -> str:
        return f"convo_state_{chat_id}"

    def set_conversation_state(self, chat_id: str, state: str, data: Optional[Dict] = None):
        """
        Establece el estado de conversación para un chat.
        
        Args:
            chat_id: ID del chat.
            state: Nombre del estado de conversación.
            data: Datos adicionales del estado.
        """
        key = self._get_conversation_state_key(chat_id)
        self.conversation_states[key] = {'state': state, 'data': data or {}}
        logger.info(f"🧠 Estado de conversación establecido para {chat_id}: {state}")

    def get_conversation_state(self, chat_id: str) -> Optional[Dict]:
        """Obtiene el estado de conversación para un chat."""
        key = self._get_conversation_state_key(chat_id)
        return self.conversation_states.get(key)

    def clear_conversation_state(self, chat_id: str):
        """Limpia el estado de conversación para un chat."""
        key = self._get_conversation_state_key(chat_id)
        if key in self.conversation_states:
            del self.conversation_states[key]
            logger.info(f"🧹 Estado de conversación limpiado para chat {chat_id}")
    
    def polling_thread(self):
        """El hilo que ejecuta el polling del bot."""
        try:
            logger.info("🤖 Bot iniciado en modo polling con python-telegram-bot")
            # Agregamos stop_signals=[] para evitar que la librería
            # intente manejar señales, lo cual falla en hilos secundarios en Linux.
            self.application.run_polling(
                drop_pending_updates=True,
                stop_signals=[]
            )
        except Exception as e:
            logger.error(f"❌ Error crítico en polling del bot: {e}", exc_info=True)

    def start_background_polling(self, interval: int = 1) -> Optional[threading.Thread]:
        """
        Inicia el polling en un hilo separado para no bloquear.
        
        Args:
            interval: Intervalo de polling (no usado directamente por la librería)
            
        Returns:
            El hilo de polling iniciado
        """
        try:
            polling_thread = threading.Thread(target=self.polling_thread, daemon=True)
            polling_thread.start()
            
            logger.info("🚀 Bot iniciado en hilo separado")
            return polling_thread
            
        except Exception as e:
            logger.error(f"❌ Error iniciando hilo de polling: {e}")
            return None
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador para texto que no es un comando."""
        chat_id = str(update.effective_chat.id) if update.effective_chat else 'unknown'
        message_text = update.message.text if update.message else ''
        
        # Verificar si hay estado de conversación
        state_info = self.get_conversation_state(chat_id)
        
        if state_info and 'state' in state_info:
            # Re-invocar el handler del comando que estableció el estado
            command = state_info['state']
            if command in self.application.handlers[0]:
                # El handler debe ser una corutina
                handler_callback = cast(CommandHandler, self.application.handlers[0][self.application.handlers[0].index(self.application.handlers[0][command])]).callback
                await handler_callback(update, context)
        elif update.message:
            # Mensaje por defecto si no hay estado y es un mensaje de texto
            await update.message.reply_text(
                "🤖 No he entendido tu mensaje.\n"
                "Usa /start para ver los comandos disponibles."
            )
            
    def _command_wrapper(self, handler: Callable) -> Callable:
        """
        Wrapper para todos los comandos para manejar chat_id y message_text.
        """
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = str(update.effective_chat.id) if update.effective_chat else None
            message_text = update.message.text if update.message else ''
            
            if not chat_id:
                logger.error("No se pudo obtener chat_id")
                return
            
            await handler(chat_id, message_text, self)
        
        return wrapped_handler