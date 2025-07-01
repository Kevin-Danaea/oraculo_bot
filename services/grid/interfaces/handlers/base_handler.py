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
from services.grid.core.trading_mode_manager import trading_mode_manager

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
    
    def get_user_config_by_type(self, chat_id: str, config_type: str) -> Optional[GridBotConfig]:
        """Obtiene la configuración específica de un tipo (ETH, BTC, AVAX)"""
        try:
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type == config_type
                ).first()
                return config
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración {config_type} del usuario: {e}")
            return None
    
    def get_all_user_configs(self, chat_id: str) -> list:
        """Obtiene todas las configuraciones del usuario (ETH, BTC, AVAX)"""
        try:
            with get_db_session() as db:
                configs = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id
                ).all()
                return configs
        except Exception as e:
            logger.error(f"❌ Error obteniendo todas las configuraciones del usuario: {e}")
            return []
    
    def save_user_config(self, chat_id: str, config_data: Dict[str, Any]) -> bool:
        """Guarda la configuración del usuario en la base de datos - SISTEMA DE 3 CONFIGURACIONES FIJAS"""
        try:
            with get_db_session() as db:
                config_type = config_data.get('config_type', 'ETH')
                
                # Buscar configuración existente del tipo
                existing_config = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type == config_type
                ).first()
                
                if existing_config:
                    # ACTUALIZAR configuración existente
                    existing_config.total_capital = config_data['total_capital']
                    existing_config.stop_loss_percent = config_data.get('stop_loss_percent', 5.0)
                    existing_config.enable_stop_loss = config_data.get('enable_stop_loss', True)
                    existing_config.enable_trailing_up = config_data.get('enable_trailing_up', True)
                    setattr(existing_config, 'is_configured', True)
                    setattr(existing_config, 'updated_at', datetime.utcnow())
                    
                    logger.info(f"✅ Configuración {config_type} actualizada para usuario {chat_id}")
                else:
                    # CREAR nueva configuración del tipo
                    default_config = GridBotConfig.get_default_config(config_type)
                    
                    new_config = GridBotConfig(
                        telegram_chat_id=chat_id,
                        config_type=config_type,
                        pair=default_config['pair'],
                        total_capital=config_data['total_capital'],
                        grid_levels=default_config['grid_levels'],
                        price_range_percent=default_config['price_range_percent'],
                        stop_loss_percent=config_data.get('stop_loss_percent', default_config['stop_loss_percent']),
                        enable_stop_loss=config_data.get('enable_stop_loss', default_config['enable_stop_loss']),
                        enable_trailing_up=config_data.get('enable_trailing_up', default_config['enable_trailing_up']),
                        is_configured=True
                    )
                    
                    db.add(new_config)
                    logger.info(f"✅ Nueva configuración {config_type} creada para usuario {chat_id}")
                
                # Desactivar otras configuraciones del usuario
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type != config_type
                ).update({'is_active': False})
                
                # Activar la configuración actual
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type == config_type
                ).update({'is_active': True})
                
                db.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error guardando configuración: {e}")
            return False
    
    def update_user_config(self, chat_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza campos específicos de la configuración activa del usuario"""
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
    
    def update_config_capital(self, chat_id: str, config_type: str, new_capital: float) -> bool:
        """Actualiza solo el capital de una configuración específica"""
        try:
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type == config_type
                ).first()
                
                if config:
                    setattr(config, 'total_capital', new_capital)
                    setattr(config, 'updated_at', datetime.utcnow())
                    db.commit()
                    logger.info(f"✅ Capital actualizado para {config_type}: ${new_capital}")
                    return True
                else:
                    logger.warning(f"⚠️ No se encontró configuración {config_type} para usuario {chat_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error actualizando capital: {e}")
            return False
    
    def activate_config(self, chat_id: str, config_type: str) -> bool:
        """Activa una configuración específica y desactiva las demás"""
        try:
            with get_db_session() as db:
                # Desactivar todas las configuraciones del usuario
                db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id
                ).update({'is_active': False})
                
                # Activar la configuración específica
                result = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.config_type == config_type
                ).update({'is_active': True})
                
                if result > 0:
                    db.commit()
                    logger.info(f"✅ Configuración {config_type} activada para usuario {chat_id}")
                    return True
                else:
                    logger.warning(f"⚠️ No se encontró configuración {config_type} para activar")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error activando configuración: {e}")
            return False
    
    def get_supported_pairs(self) -> list:
        """Lista de pares soportados - Ahora incluye ETH, BTC, AVAX"""
        return ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT']
    
    def get_supported_config_types(self) -> list:
        """Lista de tipos de configuración soportados"""
        return ['ETH', 'BTC', 'AVAX']
    
    def get_config_type_from_pair(self, pair: str) -> str:
        """Obtiene el tipo de configuración basado en el par"""
        pair_mapping = {
            'ETH/USDT': 'ETH',
            'BTC/USDT': 'BTC', 
            'AVAX/USDT': 'AVAX'
        }
        return pair_mapping.get(pair, 'ETH')
    
    def calculate_optimal_config(self, pair: str, capital: float) -> Dict[str, Any]:
        """
        Calcula configuración óptima basada en parámetros validados de backtesting.
        
        PARÁMETROS ÓPTIMOS VALIDADOS:
        - 30 niveles de grid
        - 10% de rango de precios
        - Stop loss activo (trailing activo para optimizar ganancias durante operación)
        - Capital mínimo: $10 USDT por orden (fórmula simplificada)
        """
        is_productive = trading_mode_manager.is_productive()
        
        # PARÁMETROS ÓPTIMOS DEL BACKTESTING (FIJOS)
        grid_levels = 30  # Validado en backtesting
        price_range = 10.0  # Validado en backtesting
        
        # NUEVA FÓRMULA SIMPLIFICADA: $10 USDT por orden
        # Cada nivel del grid necesita $10 USDT para operar eficientemente
        capital_minimo_por_nivel = 10  # USDT por nivel (fórmula simplificada)
        min_capital_required = grid_levels * capital_minimo_por_nivel  # 30 * 10 = $300
        
        # Configuración de capital según modo
        if not is_productive:  # Modo Sandbox
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
        
        # Obtener tipo de configuración basado en el par
        config_type = self.get_config_type_from_pair(pair)
        
        return {
            'pair': pair,
            'total_capital': final_capital,
            'grid_levels': grid_levels,
            'price_range_percent': price_range,
            'stop_loss_percent': stop_loss,
            'enable_stop_loss': True,  # Siempre activado por defecto
            'enable_trailing_up': True,  # REACTIVADO: Optimiza ganancias durante operación
            'capital_minimo_sugerido': min_capital_required if is_productive else None,
            'capital_minimo_por_nivel': capital_minimo_por_nivel,
            'modo_trading': 'PRODUCTIVO' if is_productive else 'SANDBOX',
            'config_type': config_type  # Nuevo campo para identificar el tipo
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