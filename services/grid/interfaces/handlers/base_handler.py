"""
Clase base para todos los handlers de comandos de Telegram.
Contiene utilidades y métodos comunes que todos los handlers pueden usar.
"""
from typing import Optional, Dict, Any, cast
from datetime import datetime

from shared.database.session import get_db_session
from shared.database.models import GridBotConfig
from shared.services.logging_config import get_logger
from shared.services.telegram_bot_service import TelegramBot

logger = get_logger(__name__)


class BaseHandler:
    """
    Clase base para todos los handlers de comandos.
    Proporciona utilidades comunes y acceso a la base de datos.
    """
    
    def __init__(self):
        """Inicializa el handler base"""
        pass
    
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
    
    def update_user_config(self, chat_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza campos específicos de la configuración del usuario"""
        try:
            with get_db_session() as db:
                # Convertir explícitamente para SQLAlchemy
                query = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True
                )
                result = query.update(cast(Dict, updates))
                
                if result > 0:
                    db.commit()
                    logger.info(f"✅ Configuración actualizada para usuario {chat_id}: {updates}")
                    return True
                else:
                    logger.warning(f"⚠️ No se encontró configuración activa para usuario {chat_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error actualizando configuración: {e}")
            return False
    
    def get_supported_pairs(self) -> list:
        """Lista de pares soportados - Por ahora solo ETH/USDT"""
        return ['ETH/USDT']  # Futuramente se agregarán más pares
    
    def calculate_optimal_config(self, pair: str, capital: float) -> Dict[str, Any]:
        """
        Calcula configuración óptima basada en parámetros validados de backtesting.
        
        PARÁMETROS ÓPTIMOS VALIDADOS:
        - 30 niveles de grid
        - 10% de rango de precios
        - Stop loss activo (trailing desactivado porque cerebro decide cuándo operar)
        - Capital mínimo considerando comisiones y seguridad
        """
        from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
        
        # PARÁMETROS ÓPTIMOS DEL BACKTESTING (FIJOS)
        grid_levels = 30  # Validado en backtesting
        price_range = 10.0  # Validado en backtesting
        
        # Calcular capital mínimo considerando comisiones y seguridad
        # Estimación: cada nivel necesita ~$25 USDT para cubrir:
        # - Comisiones de Binance (0.1% por trade)
        # - Spread entre compra/venta
        # - Fluctuaciones del 10% de rango
        # - Liquidez para recompras
        capital_minimo_por_nivel = 25  # USDT por nivel
        min_capital_required = grid_levels * capital_minimo_por_nivel  # 30 * 25 = $750
        
        # Configuración de capital según modo
        if not MODO_PRODUCTIVO:  # Modo Sandbox
            # Sandbox siempre usa 1000 USDT
            final_capital = 1000.0
            stop_loss = 5.0
        else:  # Modo Productivo
            if capital < min_capital_required:
                # Si no tiene suficiente capital, usar el mínimo requerido
                final_capital = min_capital_required
                stop_loss = 3.0  # Más conservador para capitales justos
            else:
                # Usar el capital que especificó
                final_capital = capital
                stop_loss = 5.0
        
        return {
            'pair': pair,
            'total_capital': final_capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range,
            'stop_loss_percent': stop_loss,
            'enable_stop_loss': True,  # Siempre activado por defecto
            'enable_trailing_up': False,  # DESACTIVADO: Cerebro decide cuándo operar
            'capital_minimo_sugerido': min_capital_required if MODO_PRODUCTIVO else None,
            'capital_minimo_por_nivel': capital_minimo_por_nivel,
            'modo_trading': 'SANDBOX' if not MODO_PRODUCTIVO else 'PRODUCTIVO'
        }
    
    def send_error_message(self, bot: TelegramBot, chat_id: str, operation: str, error: Optional[Exception] = None):
        """Envía un mensaje de error estandarizado"""
        error_msg = f"❌ Error en {operation}"
        if error:
            logger.error(f"❌ Error en {operation}: {error}")
        else:
            logger.error(f"❌ Error en {operation}")
        bot.send_message(chat_id, error_msg)
    
    def format_timestamp(self, timestamp: datetime) -> str:
        """Formatea un timestamp para mostrar en Telegram"""
        return timestamp.strftime('%Y-%m-%d %H:%M')
    
    def validate_config_exists(self, bot: TelegramBot, chat_id: str) -> Optional[GridBotConfig]:
        """Valida que el usuario tenga configuración y la retorna, sino envía mensaje de error"""
        user_config = self.get_user_config(chat_id)
        if not user_config:
            bot.send_message(chat_id, "⚠️ Primero configura el bot con /config")
            return None
        return user_config 