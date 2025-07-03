"""
Repositorio de base de datos para el servicio Grid.
"""
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.domain.interfaces import GridRepository
from app.domain.entities import GridConfig, GridOrder, GridBotState
from shared.database.models import GridBotConfig, GridBotState as GridBotStateModel, EstrategiaStatus
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseGridRepository(GridRepository):
    """Implementación del repositorio de grid usando SQLAlchemy."""

    def __init__(self, db_session: Session):
        self.db = db_session
        logger.info("✅ DatabaseGridRepository inicializado.")

    def get_active_configs(self) -> List[GridConfig]:
        """
        Obtiene configuraciones que están actualmente ejecutándose (is_running=True).
        CONFIA en el caso de uso de transiciones para gestionar is_running correctamente.
        """
        try:
            configs = self.db.query(GridBotConfig).filter(
                and_(
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True,
                    GridBotConfig.is_running == True  # El caso de uso ya gestionó las transiciones
                )
            ).all()
            
            active_configs = []
            for config in configs:
                # SOLO convertir a entidad, sin validar decisiones
                # El is_running=True ya garantiza que debe monitorearse
                active_configs.append(self._map_config_to_entity(config))
            
            logger.info(f"📊 Encontradas {len(active_configs)} configuraciones ejecutándose")
            return active_configs
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuraciones activas: {e}")
            return []

    def get_configs_with_decisions(self) -> List[Tuple[GridConfig, str, str]]:
        """
        Obtiene TODAS las configuraciones con sus decisiones actuales y estado anterior.
        SOLO consulta datos, sin evaluar lógica de decisiones.
        
        Returns:
            List[Tuple[GridConfig, current_decision, previous_state]]
        """
        try:
            configs = self.db.query(GridBotConfig).filter(
                and_(
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                )
            ).all()
            
            configs_with_decisions = []
            for config in configs:
                # Obtener decisión actual del Cerebro (SOLO consulta, sin lógica)
                estrategia = self.db.query(EstrategiaStatus).filter(
                    and_(
                        EstrategiaStatus.par == config.pair,
                        EstrategiaStatus.estrategia == "GRID"
                    )
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                
                if estrategia:
                    current_decision = estrategia.decision
                    previous_state = getattr(config, 'last_decision', 'NO_DECISION')
                    
                    grid_config = self._map_config_to_entity(config)
                    configs_with_decisions.append((grid_config, current_decision, previous_state))
                else:
                    # Si no hay estrategia, incluir con decisión vacía
                    current_decision = "NO_STRATEGY"
                    previous_state = getattr(config, 'last_decision', 'NO_DECISION')
                    
                    grid_config = self._map_config_to_entity(config)
                    configs_with_decisions.append((grid_config, current_decision, previous_state))
            
            logger.info(f"📋 Consultadas {len(configs_with_decisions)} configuraciones con decisiones")
            return configs_with_decisions
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuraciones con decisiones: {e}")
            return []

    def get_config_by_pair(self, pair: str) -> Optional[GridConfig]:
        """Obtiene la configuración para un par específico. SOLO consulta datos."""
        try:
            config = self.db.query(GridBotConfig).filter(
                and_(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                )
            ).first()
            
            if config:
                # SOLO retornar la configuración sin validar estrategias
                # Las validaciones de decisiones son responsabilidad de los casos de uso
                return self._map_config_to_entity(config)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración para {pair}: {e}")
            return None

    def update_config_status(self, config_id: int, is_running: bool, last_decision: str) -> None:
        """Actualiza el estado de una configuración."""
        try:
            config = self.db.query(GridBotConfig).filter(GridBotConfig.id == config_id).first()
            if config:
                config.is_running = is_running  # type: ignore
                config.last_decision = last_decision  # type: ignore
                config.last_decision_timestamp = datetime.utcnow()  # type: ignore
                config.updated_at = datetime.utcnow()  # type: ignore
                self.db.commit()
                logger.info(f"✅ Estado actualizado para config {config_id}: running={is_running}, decision={last_decision}")
            else:
                logger.warning(f"⚠️ No se encontró configuración con ID {config_id}")
                
        except Exception as e:
            logger.error(f"❌ Error actualizando estado de config {config_id}: {e}")
            self.db.rollback()

    def get_bot_state(self, pair: str) -> Optional[GridBotState]:
        """Obtiene el estado completo de un bot para un par."""
        try:
            # Por ahora retornamos None ya que el modelo GridBotState no está completamente implementado
            # En una implementación completa, aquí consultaríamos la tabla de estado del bot
            logger.info(f"📊 Consultando estado del bot para {pair}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del bot para {pair}: {e}")
            return None

    def save_bot_state(self, bot_state: GridBotState) -> None:
        """Guarda el estado completo de un bot."""
        try:
            # Por ahora solo loggeamos ya que el modelo completo no está implementado
            logger.info(f"💾 Guardando estado del bot {bot_state.pair}")
            # En una implementación completa, aquí guardaríamos en la tabla grid_bot_state
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado del bot {bot_state.pair}: {e}")

    def get_active_orders(self, pair: str) -> List[GridOrder]:
        """Obtiene las órdenes activas para un par."""
        try:
            # Por ahora retornamos lista vacía ya que no tenemos tabla de órdenes implementada
            # En una implementación completa, aquí consultaríamos la tabla de órdenes
            logger.info(f"📋 Consultando órdenes activas para {pair}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo órdenes activas para {pair}: {e}")
            return []

    def save_order(self, order: GridOrder) -> GridOrder:
        """Guarda una orden de grid trading."""
        try:
            # Por ahora solo loggeamos ya que no tenemos tabla de órdenes implementada
            logger.info(f"💾 Guardando orden {order.side} {order.amount} {order.pair} a ${order.price}")
            # En una implementación completa, aquí guardaríamos en la tabla de órdenes
            return order
            
        except Exception as e:
            logger.error(f"❌ Error guardando orden: {e}")
            return order

    def update_order_status(self, order_id: str, status: str, filled_at: Optional[datetime] = None) -> None:
        """Actualiza el estado de una orden."""
        try:
            # Por ahora solo loggeamos ya que no tenemos tabla de órdenes implementada
            logger.info(f"🔄 Actualizando orden {order_id} a estado {status}")
            # En una implementación completa, aquí actualizaríamos en la tabla de órdenes
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estado de orden {order_id}: {e}")

    def cancel_all_orders_for_pair(self, pair: str) -> int:
        """
        Marca como canceladas todas las órdenes activas de un par en BD.
        Retorna el número de órdenes canceladas.
        """
        try:
            # Por ahora solo loggeamos ya que no tenemos tabla de órdenes implementada
            # En una implementación completa, aquí marcaríamos órdenes como 'cancelled'
            logger.info(f"🚫 Cancelando todas las órdenes de {pair} en BD")
            
            # Simulamos que se cancelaron algunas órdenes
            cancelled_count = 0  # En implementación real: UPDATE orders SET status='cancelled' WHERE pair=pair AND status='open'
            
            logger.info(f"✅ {cancelled_count} órdenes canceladas en BD para {pair}")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"❌ Error cancelando órdenes en BD para {pair}: {e}")
            return 0

    def _map_config_to_entity(self, config: GridBotConfig) -> GridConfig:
        """Convierte un modelo de BD a entidad de dominio."""
        return GridConfig(
            id=config.id,  # type: ignore
            telegram_chat_id=config.telegram_chat_id,  # type: ignore
            config_type=config.config_type,  # type: ignore
            pair=config.pair,  # type: ignore
            total_capital=config.total_capital,  # type: ignore
            grid_levels=config.grid_levels,  # type: ignore
            price_range_percent=config.price_range_percent,  # type: ignore
            stop_loss_percent=config.stop_loss_percent,  # type: ignore
            enable_stop_loss=config.enable_stop_loss,  # type: ignore
            enable_trailing_up=config.enable_trailing_up,  # type: ignore
            is_active=config.is_active,  # type: ignore
            is_configured=config.is_configured,  # type: ignore
            is_running=config.is_running,  # type: ignore
            last_decision=config.last_decision,  # type: ignore
            last_decision_timestamp=config.last_decision_timestamp,  # type: ignore
            created_at=config.created_at,  # type: ignore
            updated_at=config.updated_at  # type: ignore
        ) 