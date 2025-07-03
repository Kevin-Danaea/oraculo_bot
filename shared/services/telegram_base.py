"""
Servicio base de Telegram unificado.
Usa exclusivamente python-telegram-bot para todas las funcionalidades.
"""
import re
import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from telegram import Update, Bot
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


class TelegramBaseService:
    """
    Servicio base de Telegram que proporciona funcionalidades básicas
    para envío de notificaciones y manejo de bots usando python-telegram-bot.
    """
    
    def __init__(self):
        """Inicializa el servicio base de Telegram."""
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("Token de Telegram no configurado")
        
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        
        # Bot para notificaciones síncronas
        self._bot = Bot(token=self.bot_token)
        
        # Aplicación para bot interactivo (opcional)
        self._application = None
        self._conversation_states: Dict[str, Dict] = {}

    def send_message(self, message: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje básico a Telegram usando python-telegram-bot.
        
        Args:
            message: Mensaje a enviar
            chat_id: ID del chat (opcional, usa el por defecto si no se especifica)
            parse_mode: 'HTML' o 'Markdown'
            
        Returns:
            True si el mensaje se envió correctamente
        """
        target_chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        
        if not target_chat_id:
            logger.error("❌ Chat ID no configurado")
            return False
        
        try:
            # Limpiar mensaje antes de enviar
            clean_message = self.clean_html_message(message)
            
            # Usar asyncio para llamar al método asíncrono del bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    self._bot.send_message(
                        chat_id=target_chat_id,
                        text=clean_message,
                        parse_mode=parse_mode
                    )
                )
                logger.info("✅ Mensaje enviado a Telegram correctamente")
                return True
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
            return False

    def clean_html_message(self, text: str) -> str:
        """
        Limpia un mensaje de caracteres HTML problemáticos para Telegram.
        Mantiene las etiquetas HTML válidas de Telegram.
        """
        try:
            text = str(text)
            
            # Reemplazar caracteres problemáticos
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # Restaurar etiquetas HTML válidas de Telegram
            valid_tags = ['b', 'i', 'code', 'pre', 'a', 'u', 's', 'tg-spoiler']
            for tag in valid_tags:
                text = text.replace(f'&lt;{tag}&gt;', f'<{tag}>')
                text = text.replace(f'&lt;{tag} /&gt;', f'<{tag}>')
                text = text.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
            
            # Limpiar espacios múltiples y caracteres problemáticos
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
                cleaned_line = ''.join(char for char in cleaned_line if char.isprintable() or char.isspace())
                cleaned_lines.append(cleaned_line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.error(f"❌ Error limpiando mensaje HTML: {e}")
            return re.sub(r'[<>]', '', str(text))

    # === FUNCIONALIDADES DE BOT INTERACTIVO ===
    
    def init_bot(self) -> bool:
        """
        Inicializa el bot interactivo usando python-telegram-bot.
        
        Returns:
            True si se inicializó correctamente
        """
        try:
            self._application = Application.builder().token(self.bot_token).build()
            
            # Registrar manejador genérico para mensajes de texto
            self._application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message)
            )
            
            logger.info("🤖 Bot interactivo inicializado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando bot: {e}")
            return False

    def register_command(self, command: str, handler: Callable):
        """
        Registra un nuevo comando en el bot.
        
        Args:
            command: Nombre del comando (ej: 'start')
            handler: Función que manejará el comando
        """
        if not self._application:
            logger.error("❌ Bot no inicializado. Llama init_bot() primero")
            return
        
        self._application.add_handler(CommandHandler(command, self._command_wrapper(handler)))
        logger.info(f"✅ Comando /{command} registrado")

    async def send_bot_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje usando el bot (asíncrono).
        
        Args:
            chat_id: ID del chat
            message: Mensaje a enviar
            parse_mode: 'HTML' o 'Markdown'
            
        Returns:
            True si el mensaje se envió correctamente
        """
        if not self._application:
            logger.error("❌ Bot no inicializado")
            return False
            
        try:
            await self._application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("✅ Mensaje enviado via bot correctamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje via bot: {e}")
            return False

    def start_polling(self) -> Optional[threading.Thread]:
        """
        Inicia el bot en modo polling en un hilo separado.
        
        Returns:
            El hilo de polling iniciado
        """
        if not self._application:
            logger.error("❌ Bot no inicializado")
            return None
            
        try:
            polling_thread = threading.Thread(target=self._polling_thread, daemon=True)
            polling_thread.start()
            logger.info("🚀 Bot iniciado en hilo separado")
            return polling_thread
            
        except Exception as e:
            logger.error(f"❌ Error iniciando polling: {e}")
            return None

    def _polling_thread(self):
        """Hilo que ejecuta el polling del bot."""
        if not self._application:
            logger.error("❌ Aplicación no inicializada")
            return
            
        asyncio.set_event_loop(asyncio.new_event_loop())
        
        try:
            logger.info("🤖 Bot iniciado en modo polling")
            self._application.run_polling(
                drop_pending_updates=True,
                stop_signals=[]
            )
        except Exception as e:
            logger.error(f"❌ Error crítico en polling: {e}", exc_info=True)

    # === GESTIÓN DE ESTADOS DE CONVERSACIÓN ===
    
    def set_conversation_state(self, chat_id: str, state: str, data: Optional[Dict] = None):
        """Establece el estado de conversación para un chat."""
        key = f"convo_state_{chat_id}"
        self._conversation_states[key] = {'state': state, 'data': data or {}}
        logger.info(f"🧠 Estado de conversación establecido para {chat_id}: {state}")

    def get_conversation_state(self, chat_id: str) -> Optional[Dict]:
        """Obtiene el estado de conversación para un chat."""
        key = f"convo_state_{chat_id}"
        return self._conversation_states.get(key)

    def clear_conversation_state(self, chat_id: str):
        """Limpia el estado de conversación para un chat."""
        key = f"convo_state_{chat_id}"
        if key in self._conversation_states:
            del self._conversation_states[key]
            logger.info(f"🧹 Estado de conversación limpiado para chat {chat_id}")

    # === MÉTODOS INTERNOS ===
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador para texto que no es un comando."""
        chat_id = str(update.effective_chat.id) if update.effective_chat else 'unknown'
        
        # Verificar si hay estado de conversación
        state_info = self.get_conversation_state(chat_id)
        
        if state_info and 'state' in state_info:
            # Re-invocar el handler del comando que estableció el estado
            # (Esta lógica puede ser personalizada por cada microservicio)
            pass
        elif update.message:
            # Mensaje por defecto
            await update.message.reply_text(
                "🤖 No he entendido tu mensaje.\n"
                "Usa /start para ver los comandos disponibles."
            )
            
    def _command_wrapper(self, handler: Callable) -> Callable:
        """Wrapper para todos los comandos."""
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = str(update.effective_chat.id) if update.effective_chat else None
            message_text = update.message.text if update.message else ''
            
            if not chat_id:
                logger.error("No se pudo obtener chat_id")
                return
            
            await handler(chat_id, message_text, self)
        
        return wrapped_handler


# Instancia global del servicio para usar en notificaciones simples
telegram_service = TelegramBaseService() 