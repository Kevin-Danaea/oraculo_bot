"""
Servicio de bot de Telegram genérico para manejar comandos e interacciones.
Versión refactorizada para usar la librería python-telegram-bot.
"""
import asyncio
import threading
from typing import Dict, Callable, Optional, Any

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """
    Clase genérica para manejar un bot de Telegram con sistema de comandos,
    usando la librería python-telegram-bot.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Inicializa el bot de Telegram
        
        Args:
            token: Token del bot de Telegram. Si no se proporciona, usa el de settings.
        """
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            logger.error("❌ No se ha configurado el token del bot de Telegram")
            raise ValueError("Token de Telegram no configurado")
        
        self.application = Application.builder().token(self.token).build()
        self.command_handlers: Dict[str, Callable] = {}
        self.conversation_states: Dict[str, Dict] = {}
        
        # El handler de mensajes de texto para conversaciones
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))

    def register_command(self, command: str, handler: Callable):
        """
        Registra un handler para un comando específico.
        
        Args:
            command: Comando sin la barra (ej: "start").
            handler: Función async que manejará el comando.
        """
        self.command_handlers[command.lower()] = handler
        self.application.add_handler(CommandHandler(command.lower(), self._command_wrapper(handler)))
        logger.info(f"✅ Comando /{command} registrado")

    def _command_wrapper(self, handler: Callable) -> Callable:
        """Crea un wrapper para pasar los argumentos correctos al handler."""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.message:
                chat_id = str(update.message.chat_id)
                text = update.message.text or ""
                await handler(chat_id, text, self)
        return wrapper

    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de texto que no son comandos (para conversaciones)."""
        if not update.message:
            return
            
        chat_id = str(update.message.chat_id)
        text = update.message.text or ""

        if chat_id in self.conversation_states:
            state = self.conversation_states[chat_id]
            handler_name = state.get('handler')
            
            if handler_name and handler_name in self.command_handlers:
                try:
                    await self.command_handlers[handler_name](chat_id, text, self)
                except Exception as e:
                    logger.error(f"❌ Error ejecutando handler de conversación '{handler_name}': {e}")
                    await self.send_message(chat_id, f"❌ Error procesando tu respuesta: {e}")
            else:
                self.clear_conversation_state(chat_id)
                await self.send_message(chat_id, "❓ Mensaje no entendido. Usa /start para ver los comandos.")
        else:
            await self.send_message(chat_id, "❓ Mensaje no entendido. Usa /start para ver los comandos.")

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML", reply_markup: Optional[Any] = None) -> bool:
        """
        Envía un mensaje a un chat específico.
        
        Args:
            chat_id: ID del chat.
            text: Texto del mensaje.
            parse_mode: Modo de parseo (HTML o MarkdownV2).
            reply_markup: Teclado inline opcional.
        """
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML if parse_mode == "HTML" else ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )
            logger.info(f"✅ Mensaje enviado a chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje a {chat_id}: {e}")
            return False

    def set_conversation_state(self, chat_id: str, handler: str, data: Optional[Dict] = None):
        """
        Establece el estado de conversación para un chat.
        
        Args:
            chat_id: ID del chat.
            handler: Nombre del handler que manejará los próximos mensajes.
            data: Datos adicionales del estado.
        """
        self.conversation_states[chat_id] = {'handler': handler, 'data': data or {}}
        logger.info(f"📱 Estado de conversación establecido para chat {chat_id}: {handler}")

    def get_conversation_state(self, chat_id: str) -> Optional[Dict]:
        """Obtiene el estado de conversación para un chat."""
        return self.conversation_states.get(chat_id)

    def clear_conversation_state(self, chat_id: str):
        """Limpia el estado de conversación para un chat."""
        if chat_id in self.conversation_states:
            del self.conversation_states[chat_id]
            logger.info(f"🧹 Estado de conversación limpiado para chat {chat_id}")

    def start_background_polling(self, interval: int = 2):
        """
        Inicia el polling en un hilo separado para no bloquear.
        
        Args:
            interval: No usado en esta versión, pero se mantiene por compatibilidad.
        """
        
        def polling_thread():
            logger.info(f"🤖 Bot iniciado en modo polling con python-telegram-bot")
            try:
                # Crear y establecer un nuevo bucle de eventos para este hilo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # run_polling es un método bloqueante, no una corutina.
                # Se ejecuta directamente en el hilo con su propio bucle de eventos.
                self.application.run_polling(drop_pending_updates=True)
            except Exception as e:
                logger.error(f"❌ Error crítico en polling del bot: {e}", exc_info=True)

        thread = threading.Thread(target=polling_thread, daemon=True, name="TelegramBotPolling")
        thread.start()
        logger.info("🚀 Bot iniciado en hilo separado")
        return thread