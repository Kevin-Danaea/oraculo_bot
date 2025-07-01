"""
Interfaz de Telegram para el Grid Trading Bot V2.
Versión refactorizada con handlers modulares especializados.
Mantiene compatibilidad total con todas las integraciones existentes.
"""
from typing import Dict, Any, Optional

from shared.services.logging_config import get_logger
from shared.services.telegram_bot_service import TelegramBot
from .handlers.basic_commands import BasicCommandsHandler
from .handlers.config_flow import ConfigFlowHandler
from ..core.trading_mode_manager import trading_mode_manager
from ..data.config_repository import get_all_active_configs_for_user

logger = get_logger(__name__)


class GridTelegramInterface:
    """
    Interfaz de Telegram para el Grid Trading Bot V2.
    Orquesta múltiples handlers especializados manteniendo la misma API externa.
    """
    
    def __init__(self, telegram_bot: TelegramBot):
        """
        Inicializa la interfaz con el bot de Telegram
        
        Args:
            telegram_bot: Instancia del bot de Telegram genérico
        """
        self.bot = telegram_bot
        
        # Inicializar handlers especializados
        self.basic_handler = BasicCommandsHandler()
        self.config_handler = ConfigFlowHandler()
        
        # Registrar comandos
        self.register_commands()
    
    def register_commands(self):
        """Registra todos los comandos esenciales del sistema multibot"""
        # Comandos esenciales del multibot (8 comandos)
        self.bot.register_command("start", self.basic_handler.handle_start_command)
        self.bot.register_command("start_bot", self.basic_handler.handle_start_bot_command)
        self.bot.register_command("stop_bot", self.basic_handler.handle_stop_bot_command)
        self.bot.register_command("status", self.basic_handler.handle_status_command)
        self.bot.register_command("balance", self.basic_handler.handle_balance_command)
        self.bot.register_command("modo_productivo", self.basic_handler.handle_modo_productivo_command)
        self.bot.register_command("modo_sandbox", self.basic_handler.handle_modo_sandbox_command)
        self.bot.register_command("estado_cerebro", self.basic_handler.handle_estado_cerebro_command)
        
        # Comandos de configuración
        self.bot.register_command("config", self.config_handler.handle_config_command)
        
        # Estados de conversación para configuración
        self.bot.register_command("config_type_selection", self.config_handler.handle_config_type_selection)
        self.bot.register_command("config_capital_input", self.config_handler.handle_capital_input)
        self.bot.register_command("config_confirmation", self.config_handler.handle_config_confirmation)
        
        logger.info("✅ Comandos esenciales del sistema multibot registrados en Telegram")
    
    # ============================================================================
    # MÉTODOS DE COMPATIBILIDAD CON LA VERSIÓN ANTERIOR
    # ============================================================================
    
    def get_supported_pairs(self) -> list:
        """Lista de pares soportados - Delegado al handler base"""
        return self.basic_handler.get_supported_pairs()
    
    def calculate_optimal_config(self, pair: str, capital: float) -> Dict[str, Any]:
        """Calcula configuración óptima - Delegado al handler base"""
        return self.basic_handler.calculate_optimal_config(pair, capital)
    
    def get_user_config(self, chat_id: str):
        """Obtiene la configuración activa del usuario - Delegado al handler base"""
        return self.basic_handler.get_user_config(chat_id)
    
    def save_user_config(self, chat_id: str, config_data: Dict[str, Any]) -> bool:
        """Guarda la configuración del usuario - Delegado al handler base"""
        return self.basic_handler.save_user_config(chat_id, config_data)
    
    # ============================================================================
    # MÉTODOS LEGACY PARA MANTENER COMPATIBILIDAD TOTAL
    # ============================================================================
    
    def handle_start_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_start_command(chat_id, message_text, bot)
    
    def handle_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_config_command(chat_id, message_text, bot)
    
    def handle_start_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_start_bot_command(chat_id, message_text, bot)
    
    def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_stop_bot_command(chat_id, message_text, bot)
    
    def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_status_command(chat_id, message_text, bot)
    
    def handle_config_type_selection(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_config_type_selection(chat_id, message_text, bot)
    
    def handle_capital_input(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_capital_input(chat_id, message_text, bot)
    
    def handle_config_confirmation(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_config_confirmation(chat_id, message_text, bot)
    
    def handle_modo_productivo_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_modo_productivo_command(chat_id, message_text, bot)
    
    def handle_modo_sandbox_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_modo_sandbox_command(chat_id, message_text, bot)
    
    def handle_estado_cerebro_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_estado_cerebro_command(chat_id, message_text, bot)
    
    def handle_balance_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_balance_command(chat_id, message_text, bot)


def get_dynamic_grid_config(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración dinámica para el grid bot.
    
    LÓGICA POR MODO:
    - SANDBOX: Configuración fija (1000 USDT, ETH/USDT, etc.) - NO consulta BD
    - PRODUCTIVO: Configuración personalizada desde la base de datos. Si no hay, la crea con mínimos.
    """
    is_productive = trading_mode_manager.is_productive()
    
    # CONFIGURACIÓN FIJA PARA MODO SANDBOX
    if not is_productive:
        logger.info("🟡 Usando configuración fija para MODO SANDBOX")
        return {
            'pair': 'ETH/USDT',
            'total_capital': 1000.0,  # Capital fijo para sandbox
            'grid_levels': 30,  # Validado en backtesting
            'price_range_percent': 10.0,  # Validado en backtesting
            'stop_loss_percent': 5.0,
            'enable_stop_loss': True,
            'enable_trailing_up': True,
            'modo': 'SANDBOX'
        }
    
    # CONFIGURACIÓN DINÁMICA PARA MODO PRODUCTIVO
    logger.info("🟢 Consultando configuración personalizada para MODO PRODUCTIVO")
    
    try:
        configs = []
        if chat_id:
            configs = get_all_active_configs_for_user(chat_id)
        
        # Si no se encuentra configuración específica, buscar cualquier configuración activa
        if not configs:
            from ..data.config_repository import get_all_active_configs
            configs = get_all_active_configs()

        if configs:
            # Usar la primera configuración activa encontrada
            config = configs[0]
            logger.info(f"✅ Usando configuración personalizada: {config['pair']} - ${config['total_capital']} USDT")
            config['modo'] = 'PRODUCTIVO'
            return config
        else:
            # Fallback a configuración mínima para modo productivo
            logger.warning("⚠️ No hay configuración personalizada, usando valores mínimos por defecto")
            return {
                'pair': 'ETH/USDT',
                'total_capital': 300.0,
                'grid_levels': 30,
                'price_range_percent': 10.0,
                'stop_loss_percent': 5.0,
                'enable_stop_loss': True,
                'enable_trailing_up': True,
                'modo': 'PRODUCTIVO'
            }
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración personalizada: {e}")
        # Fallback a configuración mínima para modo productivo
        return {
            'pair': 'ETH/USDT',
            'total_capital': 300.0,
            'grid_levels': 30,
            'price_range_percent': 10.0,
            'stop_loss_percent': 5.0,
            'enable_stop_loss': True,
            'enable_trailing_up': True,
            'modo': 'PRODUCTIVO'
        } 