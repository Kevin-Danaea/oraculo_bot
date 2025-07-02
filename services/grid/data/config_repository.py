"""
Configuration Repository
========================

Handles database operations related to Grid Bot configurations.
"""
from shared.database.session import get_db_session
from shared.database.models import GridBotConfig, EstrategiaStatus
from shared.services.logging_config import get_logger
from datetime import datetime
from typing import List, Dict, Any

logger = get_logger(__name__)


def get_all_active_configs_for_user(chat_id: str) -> List[Dict[str, Any]]:
    """
    Gets all active and configured grid bot configurations for a specific user.
    Only returns configurations that have a corresponding GRID strategy in estrategia_status.
    """
    return _get_configs(chat_id=chat_id, only_active=True)

def get_all_active_configs() -> List[Dict[str, Any]]:
    """
    Gets all active and configured grid bot configurations in the system.
    Only returns configurations that have a corresponding GRID strategy in estrategia_status.
    """
    return _get_configs(chat_id="all", only_active=True)


def _get_configs(chat_id: str, only_active: bool) -> List[Dict[str, Any]]:
    """
    Internal function to fetch configurations from the database.
    Only returns configurations that have a corresponding GRID strategy in estrategia_status.
    
    Args:
        chat_id: The user's chat_id, or "all" for all users.
        only_active: If True, returns only active and configured bots.
    """
    try:
        with get_db_session() as db:
            query = db.query(GridBotConfig)
            
            if only_active:
                query = query.filter(
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                )
            
            if chat_id != "all":
                query = query.filter(GridBotConfig.telegram_chat_id == chat_id)

            configs = query.all()
            
            if not configs:
                logger.warning(f"⚠️ No se encontraron configuraciones para los criterios: chat_id={chat_id}, active={only_active}")
                return []

            # Filtrar solo configuraciones que tienen estrategia GRID
            configuraciones_filtradas = []
            for config in configs:
                # Verificar que existe una estrategia GRID para este par
                estrategia_status = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == config.pair,
                    EstrategiaStatus.estrategia == "GRID"
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                
                if estrategia_status:
                    configuraciones_filtradas.append({
                        'pair': config.pair,
                        'config_type': config.config_type,
                        'total_capital': config.total_capital,
                        'grid_levels': config.grid_levels,
                        'price_range_percent': config.price_range_percent,
                        'last_decision': getattr(config, 'last_decision', 'NO_DECISION'),
                        'is_running': getattr(config, 'is_running', False),
                        'telegram_chat_id': config.telegram_chat_id
                    })
                else:
                    logger.info(f"ℹ️ Configuración {config.pair} ignorada - no tiene estrategia GRID en estrategia_status")

            logger.info(f"✅ Encontradas {len(configuraciones_filtradas)} configuraciones GRID para chat_id: {chat_id}")
            return configuraciones_filtradas
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuraciones de BD: {e}")
        return []

def create_default_configs_for_user(db_session, chat_id: str) -> List[GridBotConfig]:
    """
    Creates the default configurations for the 3 supported pairs for a user.
    
    Args:
        db_session: The database session.
        chat_id: ID of the chat/user.
        
    Returns:
        List of created configurations.
    """
    try:
        default_configs_data = [
            {
                'config_type': 'ETH', 'pair': 'ETH/USDT', 'total_capital': 1000.0,
                'grid_levels': 30, 'price_range_percent': 10.0
            },
            {
                'config_type': 'BTC', 'pair': 'BTC/USDT', 'total_capital': 1000.0,
                'grid_levels': 30, 'price_range_percent': 7.5
            },
            {
                'config_type': 'AVAX', 'pair': 'AVAX/USDT', 'total_capital': 1000.0,
                'grid_levels': 30, 'price_range_percent': 10.0
            }
        ]
        
        created_configs = []
        
        for config_data in default_configs_data:
            existing = db_session.query(GridBotConfig).filter(
                GridBotConfig.telegram_chat_id == chat_id,
                GridBotConfig.config_type == config_data['config_type']
            ).first()
            
            if not existing:
                new_config = GridBotConfig(
                    telegram_chat_id=chat_id,
                    config_type=config_data['config_type'],
                    pair=config_data['pair'],
                    total_capital=config_data['total_capital'],
                    grid_levels=config_data['grid_levels'],
                    price_range_percent=config_data['price_range_percent'],
                    stop_loss_percent=5.0,
                    enable_stop_loss=True,
                    enable_trailing_up=True,
                    is_active=True,
                    is_configured=True,
                    is_running=False,
                    last_decision='NO_DECISION',
                    last_decision_timestamp=datetime.utcnow()
                )
                db_session.add(new_config)
                created_configs.append(new_config)
                logger.info(f"✅ Configuración creada: {config_data['pair']} con ${config_data['total_capital']}")
            else:
                existing.is_active = True
                existing.is_configured = True
                existing.total_capital = config_data['total_capital']
                created_configs.append(existing)
                logger.info(f"✅ Configuración actualizada: {config_data['pair']} con ${config_data['total_capital']}")
        
        db_session.commit()
        logger.info(f"✅ {len(created_configs)} configuraciones por defecto creadas/actualizadas para {chat_id}")
        
        return created_configs
        
    except Exception as e:
        logger.error(f"❌ Error creando configuraciones por defecto: {e}")
        db_session.rollback()
        return [] 