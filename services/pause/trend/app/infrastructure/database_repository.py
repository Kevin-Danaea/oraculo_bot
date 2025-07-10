"""Repository for trend bot using database persistence."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from shared.database.session import get_db_session
from shared.database.models import TrendBotConfig, EstrategiaStatus
from ..domain.entities import TrendBotStatus, TrendPosition, TrendBotMetrics
from ..domain.interfaces import ITrendBotRepository

logger = logging.getLogger(__name__)


class DatabaseTrendBotRepository(ITrendBotRepository):
    """Implementación del repositorio usando base de datos para persistencia."""
    
    def __init__(self):
        logger.info("✅ DatabaseTrendBotRepository inicializado")
    
    async def save_bot_status(self, status: TrendBotStatus) -> None:
        """Guarda el estado del bot en la base de datos."""
        try:
            with get_db_session() as session:
                # LINTER: session nunca es None aquí, ya que si lo fuera lanzamos excepción antes
                if session is None:
                    raise Exception("No se pudo obtener sesión de base de datos")
                config = session.query(TrendBotConfig).filter(
                    and_(
                        TrendBotConfig.telegram_chat_id == status.bot_id,
                        TrendBotConfig.pair == status.symbol
                    )
                ).first()
                if config:
                    # Actualizar configuración existente
                    object.__setattr__(config, 'is_running', (status.state.value == 'EN_POSICION'))
                    object.__setattr__(config, 'updated_at', datetime.utcnow())
                else:
                    config = TrendBotConfig(
                        telegram_chat_id=status.bot_id,
                        pair=status.symbol,
                        capital_allocation=300.0,
                        trailing_stop_percent=20.0,
                        is_active=True,
                        is_running=(status.state.value == 'EN_POSICION')
                    )
                    session.add(config)
                session.commit()
                logger.debug(f"Estado del bot {status.bot_id} guardado en BD")
        except Exception as e:
            logger.error(f"Error guardando estado del bot en BD: {str(e)}")
            raise
    
    async def get_bot_status(self, bot_id: str) -> Optional[TrendBotStatus]:
        """Obtiene el estado del bot desde la base de datos."""
        try:
            with get_db_session() as session:
                # LINTER: session nunca es None aquí, ya que si lo fuera lanzamos excepción antes
                if session is None:
                    raise Exception("No se pudo obtener sesión de base de datos")
                config = session.query(TrendBotConfig).filter(
                    TrendBotConfig.telegram_chat_id == bot_id
                ).first()
                if not config:
                    return None
                brain_decision = session.query(EstrategiaStatus).filter(
                    and_(
                        EstrategiaStatus.par == config.pair,
                        EstrategiaStatus.estrategia == 'TREND'
                    )
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                state = 'EN_POSICION' if bool(getattr(config, 'is_running', False)) else 'FUERA_DEL_MERCADO'
                from ..domain.entities import TrendBotState, BrainDecision
                updated_at = getattr(config, 'updated_at', None)
                if not isinstance(updated_at, datetime):
                    updated_at = None
                return TrendBotStatus(
                    bot_id=str(config.telegram_chat_id),
                    symbol=str(config.pair),
                    state=TrendBotState(state),
                    current_position=None,
                    last_decision=BrainDecision(brain_decision.decision) if brain_decision else None,
                    last_update=updated_at
                )
        except Exception as e:
            logger.error(f"Error obteniendo estado del bot desde BD: {str(e)}")
            return None
    
    async def save_position(self, position: TrendPosition) -> None:
        """Guarda una posición (no implementado - usamos estado simple)."""
        # Para simplicidad, no guardamos posiciones individuales
        # Solo actualizamos el estado del bot
        logger.debug(f"Posición {position.id} registrada (estado simple)")
    
    async def get_current_position(self, bot_id: str) -> Optional[TrendPosition]:
        """Obtiene la posición actual del bot (no implementado - estado simple)."""
        # Para simplicidad, no mantenemos posiciones individuales
        return None
    
    async def save_metrics(self, bot_id: str, metrics: TrendBotMetrics) -> None:
        """Guarda las métricas del bot (no implementado - estado simple)."""
        # Para simplicidad, no guardamos métricas detalladas
        logger.debug(f"Métricas del bot {bot_id} registradas (estado simple)")
    
    async def get_metrics(self, bot_id: str) -> Optional[TrendBotMetrics]:
        """Obtiene las métricas del bot (no implementado - estado simple)."""
        # Para simplicidad, retornamos métricas vacías
        from ..domain.entities import TrendBotMetrics
        return TrendBotMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=Decimal('0'),
            total_fees=Decimal('0'),
            best_trade=Decimal('0'),
            worst_trade=Decimal('0'),
            average_holding_time_hours=0.0,
            win_rate=0.0
        )
    
    async def get_config(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración del bot."""
        try:
            with get_db_session() as session:
                # LINTER: session nunca es None aquí, ya que si lo fuera lanzamos excepción antes
                if session is None:
                    raise Exception("No se pudo obtener sesión de base de datos")
                config = session.query(TrendBotConfig).filter(
                    TrendBotConfig.telegram_chat_id == bot_id
                ).first()
                
                if not config:
                    return None
                
                return config.to_dict()
                
        except Exception as e:
            logger.error(f"Error obteniendo configuración del bot: {str(e)}")
            return None
    
    async def save_config(self, bot_id: str, config_data: Dict[str, Any]) -> None:
        """Guarda la configuración del bot."""
        try:
            pair = config_data.get('pair', 'ETH/USDT')
            with get_db_session() as session:
                # LINTER: session nunca es None aquí, ya que si lo fuera lanzamos excepción antes
                if session is None:
                    raise Exception("No se pudo obtener sesión de base de datos")
                config = session.query(TrendBotConfig).filter(
                    and_(
                        TrendBotConfig.telegram_chat_id == bot_id,
                        TrendBotConfig.pair == pair
                    )
                ).first()
                if config:
                    config.capital_allocation = config_data.get('capital_allocation', 300.0)
                    config.trailing_stop_percent = config_data.get('trailing_stop_percent', 20.0)
                    config.is_active = config_data.get('is_active', True)
                    object.__setattr__(config, 'updated_at', datetime.utcnow())
                    logger.debug(f"✅ Configuración actualizada para {bot_id} - {pair}")
                else:
                    config = TrendBotConfig(
                        telegram_chat_id=bot_id,
                        pair=pair,
                        capital_allocation=config_data.get('capital_allocation', 300.0),
                        trailing_stop_percent=config_data.get('trailing_stop_percent', 20.0),
                        is_active=config_data.get('is_active', True)
                    )
                    session.add(config)
                    logger.debug(f"🆕 Nueva configuración creada para {bot_id} - {pair}")
                session.commit()
                logger.debug(f"Configuración del bot {bot_id} - {pair} guardada")
        except Exception as e:
            logger.error(f"Error guardando configuración del bot: {str(e)}")
            raise 