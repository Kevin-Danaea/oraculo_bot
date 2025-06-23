"""
Servicio de bot de Telegram genérico para manejar comandos e interacciones.
Diseñado para ser reutilizado por diferentes servicios con diferentes lógicas de comandos.
"""
import requests
import json
from typing import Dict, Callable, Optional, Any, Union
from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """
    Clase genérica para manejar un bot de Telegram con sistema de comandos.
    Permite registrar handlers para diferentes comandos y manejar conversaciones.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Inicializa el bot de Telegram
        
        Args:
            token: Token del bot de Telegram. Si no se proporciona, usa el de settings
        """
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.command_handlers: Dict[str, Callable] = {}
        self.conversation_states: Dict[str, Dict] = {}  # Estados de conversación por chat_id
        self.last_update_id = 0
        
        if not self.token:
            logger.error("❌ No se ha configurado el token del bot de Telegram")
            raise ValueError("Token de Telegram no configurado")
    
    def register_command(self, command: str, handler: Callable):
        """
        Registra un handler para un comando específico
        
        Args:
            command: Comando sin la barra (ej: "start", "config")
            handler: Función que manejará el comando. Debe recibir (chat_id, message_text, bot_instance)
        """
        self.command_handlers[command.lower()] = handler
        logger.info(f"✅ Comando /{command} registrado")
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML", reply_markup: Optional[Dict] = None) -> bool:
        """
        Envía un mensaje a un chat específico
        
        Args:
            chat_id: ID del chat
            text: Texto del mensaje
            parse_mode: Modo de parseo (HTML o Markdown)
            reply_markup: Teclado inline opcional
        """
        try:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/sendMessage", data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Mensaje enviado a chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Error enviando mensaje: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            return False
    
    def get_updates(self) -> list:
        """
        Obtiene las actualizaciones pendientes del bot
        """
        try:
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 5,
                'allowed_updates': ['message']
            }
            
            response = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    updates = data['result']
                    if updates:
                        self.last_update_id = max(update['update_id'] for update in updates)
                    return updates
                else:
                    logger.error(f"❌ Error en API de Telegram: {data}")
                    return []
            else:
                logger.error(f"❌ Error obteniendo updates: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo updates: {e}")
            return []
    
    def process_message(self, message: Dict):
        """
        Procesa un mensaje recibido y ejecuta el handler correspondiente
        
        Args:
            message: Objeto message de Telegram
        """
        try:
            chat_id = str(message['chat']['id'])
            text = message.get('text', '').strip()
            
            if not text:
                return
            
            # Verificar si es un comando
            if text.startswith('/'):
                command = text[1:].split()[0].lower()  # Extraer comando sin argumentos
                
                if command in self.command_handlers:
                    logger.info(f"📱 Ejecutando comando /{command} para chat {chat_id}")
                    try:
                        self.command_handlers[command](chat_id, text, self)
                    except Exception as e:
                        logger.error(f"❌ Error ejecutando comando /{command}: {e}")
                        self.send_message(
                            chat_id, 
                            f"❌ Error ejecutando comando: {str(e)}"
                        )
                else:
                    # Comando no reconocido
                    available_commands = ", ".join([f"/{cmd}" for cmd in self.command_handlers.keys()])
                    self.send_message(
                        chat_id,
                        f"❌ Comando no reconocido.\n\n🤖 Comandos disponibles:\n{available_commands}"
                    )
            else:
                # No es un comando, verificar si hay estado de conversación
                if chat_id in self.conversation_states:
                    state = self.conversation_states[chat_id]
                    handler_name = state.get('handler')
                    
                    if handler_name and handler_name in self.command_handlers:
                        # Continuar conversación
                        self.command_handlers[handler_name](chat_id, text, self)
                    else:
                        # Estado inválido, limpiar
                        self.clear_conversation_state(chat_id)
                        self.send_message(
                            chat_id,
                            "❓ Mensaje no entendido. Usa /start para ver los comandos disponibles."
                        )
                else:
                    # No hay estado de conversación
                    self.send_message(
                        chat_id,
                        "❓ Mensaje no entendido. Usa /start para ver los comandos disponibles."
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
    
    def set_conversation_state(self, chat_id: str, handler: str, data: Optional[Dict] = None):
        """
        Establece el estado de conversación para un chat
        
        Args:
            chat_id: ID del chat
            handler: Nombre del handler que manejará los próximos mensajes
            data: Datos adicionales del estado
        """
        self.conversation_states[chat_id] = {
            'handler': handler,
            'data': data or {}
        }
        logger.info(f"📱 Estado de conversación establecido para chat {chat_id}: {handler}")
    
    def get_conversation_state(self, chat_id: str) -> Optional[Dict]:
        """
        Obtiene el estado de conversación para un chat
        """
        return self.conversation_states.get(chat_id)
    
    def clear_conversation_state(self, chat_id: str):
        """
        Limpia el estado de conversación para un chat
        """
        if chat_id in self.conversation_states:
            del self.conversation_states[chat_id]
            logger.info(f"🧹 Estado de conversación limpiado para chat {chat_id}")
    
    def run_polling(self, interval: int = 2):
        """
        Ejecuta el bot en modo polling (bucle infinito)
        
        Args:
            interval: Intervalo en segundos entre verificaciones
        """
        import time
        
        logger.info(f"🤖 Bot iniciado en modo polling (intervalo: {interval}s)")
        
        try:
            while True:
                updates = self.get_updates()
                
                for update in updates:
                    if 'message' in update:
                        self.process_message(update['message'])
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Bot detenido por interrupción manual")
        except Exception as e:
            logger.error(f"❌ Error en polling del bot: {e}")
            raise
    
    def start_background_polling(self, interval: int = 2):
        """
        Inicia el polling en un hilo separado para no bloquear
        
        Args:
            interval: Intervalo en segundos entre verificaciones
        """
        import threading
        
        def polling_thread():
            self.run_polling(interval)
        
        thread = threading.Thread(target=polling_thread, daemon=True, name="TelegramBotPolling")
        thread.start()
        logger.info("🚀 Bot iniciado en hilo separado")
        return thread