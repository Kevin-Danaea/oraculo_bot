"""
Repositorio de base de datos para el servicio Grid.
"""
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import OperationalError, DisconnectionError

from app.domain.interfaces import GridRepository
from app.domain.entities import GridConfig, GridOrder, GridBotState, GridStep, GridTrade
from shared.database.models import GridBotConfig, GridBotState as GridBotStateModel, EstrategiaStatus
from shared.database.session import get_db_session, health_check
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseGridRepository(GridRepository):
    """Implementación del repositorio de grid usando SQLAlchemy con manejo robusto de conexiones."""

    def __init__(self, db_session: Session):
        self.db = db_session
        logger.info("✅ DatabaseGridRepository inicializado.")

        # --- Almacenamiento temporal de GridStep en memoria ---
        # Clave: pair, Valor: List[GridStep]
        self._grid_steps_store: Dict[str, List[GridStep]] = {}

    def _ensure_connection(self):
        """
        Verifica y restaura la conexión si es necesario.
        """
        if self.db is None:
            from shared.database.session import get_db_with_retry
            self.db = get_db_with_retry()
            return
            
        try:
            # Verificar que la conexión está activa
            from sqlalchemy import text
            self.db.execute(text("SELECT 1"))
        except (OperationalError, DisconnectionError) as e:
            logger.warning(f"⚠️ Conexión perdida, intentando restaurar: {e}")
            # La sesión actual está corrupta, crear una nueva
            try:
                self.db.close()
            except:
                pass
            # Obtener nueva sesión con reintentos
            from shared.database.session import get_db_with_retry
            self.db = get_db_with_retry()
            logger.info("✅ Conexión restaurada")

    def get_active_configs(self) -> List[GridConfig]:
        """
        Obtiene configuraciones que están actualmente ejecutándose (is_running=True).
        CONFIA en el caso de uso de transiciones para gestionar is_running correctamente.
        """
        try:
            self._ensure_connection()
            
            if self.db is None:
                logger.error("❌ No se pudo obtener conexión a la base de datos")
                return []
            
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
            self._ensure_connection()
            
            if self.db is None:
                logger.error("❌ No se pudo obtener conexión a la base de datos")
                return []
            
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
            self._ensure_connection()
            
            if self.db is None:
                logger.error("❌ No se pudo obtener conexión a la base de datos")
                return None
            
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
            self._ensure_connection()
            
            if self.db is None:
                logger.error("❌ No se pudo obtener conexión a la base de datos")
                return
            
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
            if self.db is not None:
                try:
                    self.db.rollback()
                except Exception as rollback_error:
                    logger.warning(f"⚠️ Error en rollback: {rollback_error}")

    def get_bot_state(self, pair: str) -> Optional[GridBotState]:
        """Obtiene el estado completo de un bot para un par."""
        try:
            self._ensure_connection()
            
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
            self._ensure_connection()
            
            # Por ahora solo loggeamos ya que el modelo completo no está implementado
            logger.info(f"💾 Guardando estado del bot {bot_state.pair}")
            # En una implementación completa, aquí guardaríamos en la tabla grid_bot_state
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado del bot {bot_state.pair}: {e}")

    def get_active_orders(self, pair: str) -> List[GridOrder]:
        """Obtiene las órdenes activas para un par."""
        try:
            self._ensure_connection()
            
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
            self._ensure_connection()
            
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
            self._ensure_connection()
            
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
            self._ensure_connection()
            
            # Por ahora solo loggeamos ya que no tenemos tabla de órdenes implementada
            logger.info(f"❌ Cancelando todas las órdenes para {pair}")
            # En una implementación completa, aquí actualizaríamos en la tabla de órdenes
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error cancelando órdenes para {pair}: {e}")
            return 0

    def health_check(self) -> bool:
        """
        Verifica la salud de la conexión a la base de datos.
        
        Returns:
            bool: True si la conexión está saludable
        """
        try:
            self._ensure_connection()
            return True
        except Exception as e:
            logger.error(f"❌ Health check falló: {e}")
            return False

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

    # ------------------------------------------------------------------
    # Implementación de métodos para gestión de GridStep
    # Estas operaciones usan almacenamiento en memoria como placeholder
    # hasta que se implemente la persistencia en base de datos.
    # ------------------------------------------------------------------

    def get_grid_steps(self, pair: str) -> List[GridStep]:
        """Obtiene la lista de GridStep almacenada en memoria para el par."""
        steps = self._grid_steps_store.get(pair, [])
        logger.debug(f"📋 get_grid_steps -> {pair}: {len(steps)} pasos almacenados")
        return steps

    def save_grid_steps(self, pair: str, steps: List[GridStep]) -> None:
        """Guarda o reemplaza la lista de GridStep para el par."""
        self._grid_steps_store[pair] = steps
        logger.debug(f"💾 save_grid_steps -> {pair}: {len(steps)} pasos guardados")

    def save_trade(self, trade: GridTrade) -> GridTrade:
        """Guarda un trade completado."""
        try:
            # Por ahora almacenamos en memoria, en producción sería en BD
            if not hasattr(self, '_trades_store'):
                self._trades_store = {}
            
            pair = trade.pair
            if pair not in self._trades_store:
                self._trades_store[pair] = []
            
            self._trades_store[pair].append(trade)
            logger.info(f"💾 Trade guardado: {trade.pair} - Profit: ${trade.profit:.4f}")
            return trade
            
        except Exception as e:
            logger.error(f"❌ Error guardando trade: {e}")
            return trade

    def get_trades_by_pair(self, pair: str, limit: int = 100) -> List[GridTrade]:
        """Obtiene los trades completados para un par específico."""
        try:
            if not hasattr(self, '_trades_store'):
                self._trades_store = {}
            
            trades = self._trades_store.get(pair, [])
            # Ordenar por fecha de ejecución (más recientes primero)
            trades.sort(key=lambda x: x.executed_at, reverse=True)
            return trades[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo trades para {pair}: {e}")
            return []

    def get_total_profit_by_pair(self, pair: str) -> Decimal:
        """Calcula el P&L total basado en trades reales para un par."""
        try:
            trades = self.get_trades_by_pair(pair)
            total_profit = sum(trade.profit for trade in trades)
            # Asegurar que el resultado sea Decimal
            if isinstance(total_profit, (int, float)):
                total_profit = Decimal(str(total_profit))
            logger.debug(f"📊 P&L total para {pair}: ${total_profit:.4f} (basado en {len(trades)} trades)")
            return total_profit
            
        except Exception as e:
            logger.error(f"❌ Error calculando P&L total para {pair}: {e}")
            return Decimal('0')

    def get_trades_summary_by_pair(self, pair: str) -> Dict[str, Any]:
        """Obtiene un resumen de trades para un par específico."""
        try:
            trades = self.get_trades_by_pair(pair)
            
            if not trades:
                return {
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_profit_percent': Decimal('0'),
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'avg_profit_per_trade': Decimal('0'),
                    'best_trade': Decimal('0'),
                    'worst_trade': Decimal('0'),
                    'win_rate': Decimal('0')
                }
            
            total_profit = sum(trade.profit for trade in trades)
            # Asegurar que total_profit sea Decimal
            if isinstance(total_profit, (int, float)):
                total_profit = Decimal(str(total_profit))
                
            winning_trades = [t for t in trades if t.profit > 0]
            losing_trades = [t for t in trades if t.profit < 0]
            
            avg_profit_per_trade = total_profit / len(trades) if trades else Decimal('0')
            best_trade = max(trade.profit for trade in trades) if trades else Decimal('0')
            worst_trade = min(trade.profit for trade in trades) if trades else Decimal('0')
            
            # Calcular porcentaje promedio de ganancia
            total_invested = sum(trade.buy_price * trade.amount for trade in trades)
            if isinstance(total_invested, (int, float)):
                total_invested = Decimal(str(total_invested))
            total_profit_percent = (total_profit / total_invested * 100) if total_invested > 0 else Decimal('0')
            
            # Calcular win rate
            win_rate = (len(winning_trades) / len(trades) * 100) if trades else Decimal('0')
            if isinstance(win_rate, (int, float)):
                win_rate = Decimal(str(win_rate))
            
            return {
                'total_trades': len(trades),
                'total_profit': total_profit,
                'total_profit_percent': total_profit_percent,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'avg_profit_per_trade': avg_profit_per_trade,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'win_rate': win_rate
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de trades para {pair}: {e}")
            return {
                'total_trades': 0,
                'total_profit': Decimal('0'),
                'total_profit_percent': Decimal('0'),
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_profit_per_trade': Decimal('0'),
                'best_trade': Decimal('0'),
                'worst_trade': Decimal('0'),
                'win_rate': Decimal('0')
            } 