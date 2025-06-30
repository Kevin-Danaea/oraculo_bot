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
from .handlers.advanced_strategies import AdvancedStrategiesHandler

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
        self.advanced_handler = AdvancedStrategiesHandler()
        
        # Registrar comandos
        self.register_commands()
    
    def register_commands(self):
        """Registra todos los comandos específicos del grid bot V2"""
        # Comandos básicos V1
        self.bot.register_command("start", self.basic_handler.handle_start_command)
        self.bot.register_command("start_bot", self.basic_handler.handle_start_bot_command)
        self.bot.register_command("stop_bot", self.basic_handler.handle_stop_bot_command)
        self.bot.register_command("restart_bot", self.basic_handler.handle_restart_bot_command)
        self.bot.register_command("status", self.basic_handler.handle_status_command)
        self.bot.register_command("delete_config", self.basic_handler.handle_delete_config_command)
        
        # Comandos de integración con Cerebro v3.0
        self.bot.register_command("modo_productivo", self.basic_handler.handle_modo_productivo_command)
        self.bot.register_command("modo_sandbox", self.basic_handler.handle_modo_sandbox_command)
        self.bot.register_command("estado_cerebro", self.basic_handler.handle_estado_cerebro_command)
        self.bot.register_command("modo_actual", self.basic_handler.handle_modo_actual_command)
        self.bot.register_command("info_config", self.basic_handler.handle_info_config_command)
        
        # Comandos de configuración
        self.bot.register_command("config", self.config_handler.handle_config_command)
        
        # Estados de conversación para configuración
        self.bot.register_command("config_pair_selection", self.config_handler.handle_pair_selection)
        self.bot.register_command("config_capital_input", self.config_handler.handle_capital_input)
        self.bot.register_command("config_confirmation", self.config_handler.handle_config_confirmation)
        
        # Comandos V2: Estrategias Avanzadas
        self.bot.register_command("enable_stop_loss", self.advanced_handler.handle_enable_stop_loss_command)
        self.bot.register_command("disable_stop_loss", self.advanced_handler.handle_disable_stop_loss_command)
        self.bot.register_command("enable_trailing", self.advanced_handler.handle_enable_trailing_command)
        self.bot.register_command("disable_trailing", self.advanced_handler.handle_disable_trailing_command)
        self.bot.register_command("set_stop_loss", self.advanced_handler.handle_set_stop_loss_command)
        self.bot.register_command("protections", self.advanced_handler.handle_protections_command)
        
        logger.info("✅ Comandos del Grid Bot V2 registrados en Telegram (versión refactorizada)")
    
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
    
    def handle_restart_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_restart_bot_command(chat_id, message_text, bot)
    
    def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_status_command(chat_id, message_text, bot)
    
    def handle_delete_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.basic_handler.handle_delete_config_command(chat_id, message_text, bot)
    
    def handle_pair_selection(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_pair_selection(chat_id, message_text, bot)
    
    def handle_capital_input(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_capital_input(chat_id, message_text, bot)
    
    def handle_config_confirmation(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.config_handler.handle_config_confirmation(chat_id, message_text, bot)
    
    def handle_enable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_enable_stop_loss_command(chat_id, message_text, bot)
    
    def handle_disable_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_disable_stop_loss_command(chat_id, message_text, bot)
    
    def handle_enable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_enable_trailing_command(chat_id, message_text, bot)
    
    def handle_disable_trailing_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_disable_trailing_command(chat_id, message_text, bot)
    
    def handle_set_stop_loss_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_set_stop_loss_command(chat_id, message_text, bot)
    
    def handle_protections_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Método legacy - delegado al handler correspondiente"""
        return self.advanced_handler.handle_protections_command(chat_id, message_text, bot)


def get_dynamic_grid_config(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración dinámica para el grid bot desde la base de datos.
    Esta función mantiene compatibilidad con el sistema existente.
    """
    # Crear una instancia temporal del handler para acceder a la funcionalidad
    from shared.services.telegram_bot_service import TelegramBot
    from shared.config.settings import settings
    
    temp_bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
    interface = GridTelegramInterface(temp_bot)
    
    try:
        config = None
        
        # Buscar configuración específica del usuario si se proporciona chat_id
        if chat_id:
            config = interface.get_user_config(chat_id)
        
        # Si no se encuentra configuración específica, buscar cualquier configuración activa
        if not config:
            # Usar el método del handler base
            from shared.database.session import get_db_session
            from shared.database.models import GridBotConfig
            
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.is_active == True
                ).first()
        
        if config:
            logger.info(f"✅ Usando configuración dinámica: {config.pair}")
            # Acceder directamente a los valores del objeto
            pair_value = config.pair
            capital_value = config.total_capital
            levels_value = config.grid_levels
            range_value = config.price_range_percent
            stop_loss_value = getattr(config, 'stop_loss_percent', 5.0)
            enable_stop_loss_value = getattr(config, 'enable_stop_loss', True)
            enable_trailing_value = getattr(config, 'enable_trailing_up', True)
            
            return {
                'pair': pair_value,
                'total_capital': capital_value,
                'grid_levels': levels_value,
                'price_range_percent': range_value,
                'stop_loss_percent': stop_loss_value,
                'enable_stop_loss': enable_stop_loss_value,
                'enable_trailing_up': enable_trailing_value
            }
        else:
            # Configuración por defecto como fallback - PARÁMETROS ÓPTIMOS VALIDADOS
            logger.warning("⚠️ No hay configuración dinámica, usando valores óptimos por defecto")
            return {
                'pair': 'ETH/USDT',
                'total_capital': 1000.0,  # Capital por defecto para sandbox
                'grid_levels': 30,  # Validado en backtesting
                'price_range_percent': 10.0,  # Validado en backtesting
                'stop_loss_percent': 5.0,
                'enable_stop_loss': True,
                'enable_trailing_up': False  # Desactivado: Cerebro decide cuándo operar
            }
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración dinámica: {e}")
        # Fallback a configuración por defecto - PARÁMETROS ÓPTIMOS VALIDADOS
        return {
            'pair': 'ETH/USDT',
            'total_capital': 1000.0,  # Capital por defecto para sandbox
            'grid_levels': 30,  # Validado en backtesting
            'price_range_percent': 10.0,  # Validado en backtesting
            'stop_loss_percent': 5.0,
            'enable_stop_loss': True,
            'enable_trailing_up': False  # Desactivado: Cerebro decide cuándo operar
        } 