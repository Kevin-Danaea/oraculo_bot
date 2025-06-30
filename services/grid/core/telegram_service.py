"""
Módulo de gestión del servicio de Telegram
Gestiona el bot de Telegram para control remoto del grid bot
"""

import threading
from typing import Optional
from shared.services.telegram_bot_service import TelegramBot
from shared.services.logging_config import get_logger
from shared.config.settings import settings
from services.grid.interfaces.telegram_interface import GridTelegramInterface

logger = get_logger(__name__)

# Variables globales para el bot de Telegram
telegram_bot: Optional[TelegramBot] = None
telegram_interface: Optional[GridTelegramInterface] = None
telegram_thread: Optional[threading.Thread] = None

def start_telegram_bot() -> Optional[TelegramBot]:
    """
    Inicia el bot de Telegram para control remoto del grid bot
    """
    global telegram_bot, telegram_interface, telegram_thread
    
    try:
        # Verificar si hay token configurado
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("⚠️ Token de Telegram no configurado - Bot de Telegram deshabilitado")
            return None
        
        # Crear instancia del bot
        telegram_bot = TelegramBot()
        
        # Crear interfaz específica del grid
        telegram_interface = GridTelegramInterface(telegram_bot)
        
        # Iniciar polling en hilo separado
        telegram_thread = telegram_bot.start_background_polling(interval=2)
        
        logger.info("🤖 Bot de Telegram iniciado correctamente")
        return telegram_bot
        
    except Exception as e:
        logger.error(f"❌ Error iniciando bot de Telegram: {e}")
        return None

def stop_telegram_bot():
    """
    Detiene el bot de Telegram
    """
    global telegram_bot, telegram_interface, telegram_thread
    
    try:
        if telegram_thread and telegram_thread.is_alive():
            logger.info("🛑 Deteniendo bot de Telegram...")
            # El hilo del bot se detendrá automáticamente al salir del programa
            telegram_thread = None
        
        telegram_bot = None
        telegram_interface = None
        
        logger.info("✅ Bot de Telegram detenido")
        
    except Exception as e:
        logger.error(f"❌ Error deteniendo bot de Telegram: {e}")

def get_telegram_bot() -> Optional[TelegramBot]:
    """
    Obtiene la instancia actual del bot de Telegram
    """
    return telegram_bot

def get_telegram_interface() -> Optional[GridTelegramInterface]:
    """
    Obtiene la interfaz actual del grid bot con Telegram
    """
    return telegram_interface

__all__ = [
    'start_telegram_bot',
    'stop_telegram_bot',
    'get_telegram_bot',
    'get_telegram_interface'
] 