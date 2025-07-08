"""
Repositorio de Decisiones
=========================

Implementación concreta del repositorio de decisiones de trading.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.interfaces import DecisionRepository
from app.domain.entities import TradingDecision, BotType, DecisionType, MarketIndicators, TradingThresholds
from shared.database.session import SessionLocal
from shared.database.models import EstrategiaStatus

logger = logging.getLogger(__name__)


class DatabaseDecisionRepository(DecisionRepository):
    """
    Implementación del repositorio de decisiones usando base de datos.
    """
    
    def __init__(self):
        """Inicializa el repositorio."""
        self.logger = logging.getLogger(__name__)
    
    async def save_decision(self, decision: TradingDecision) -> bool:
        """
        Guarda o actualiza una decisión de trading en la base de datos.
        Si ya existe una decisión para el par y estrategia, la actualiza.
        
        Args:
            decision: Decisión a guardar
            
        Returns:
            True si se guardó correctamente
        """
        try:
            db = SessionLocal()
            
            try:
                # Buscar decisión existente para el par y estrategia
                existing_decision = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == decision.pair,
                    EstrategiaStatus.estrategia == decision.bot_type.value
                ).first()
                
                if existing_decision:
                    # Actualizar decisión existente usando update()
                    db.query(EstrategiaStatus).filter(
                        EstrategiaStatus.par == decision.pair,
                        EstrategiaStatus.estrategia == decision.bot_type.value
                    ).update({
                        'decision': decision.decision.value,
                        'razon': decision.reason,
                        'adx_actual': decision.indicators.adx,
                        'volatilidad_actual': decision.indicators.volatility,
                        'sentiment_promedio': decision.indicators.sentiment,
                        'umbral_adx': decision.thresholds.adx_threshold,
                        'umbral_volatilidad': decision.thresholds.volatility_threshold,
                        'umbral_sentimiento': decision.thresholds.sentiment_threshold,
                        'timestamp': decision.timestamp
                    })
                    
                    db.commit()
                    self.logger.info(f"✅ Decisión actualizada para {decision.pair}: {decision.decision.value}")
                else:
                    # Crear nueva decisión
                    db_decision = EstrategiaStatus(
                        par=decision.pair,
                        estrategia=decision.bot_type.value,
                        decision=decision.decision.value,
                        razon=decision.reason,
                        adx_actual=decision.indicators.adx,
                        volatilidad_actual=decision.indicators.volatility,
                        sentiment_promedio=decision.indicators.sentiment,
                        umbral_adx=decision.thresholds.adx_threshold,
                        umbral_volatilidad=decision.thresholds.volatility_threshold,
                        umbral_sentimiento=decision.thresholds.sentiment_threshold,
                        timestamp=decision.timestamp
                    )
                    
                    db.add(db_decision)
                    db.commit()
                    db.refresh(db_decision)
                    self.logger.info(f"✅ Nueva decisión creada para {decision.pair}: {decision.decision.value}")
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando decisión para {decision.pair}: {e}")
            return False
    
    async def get_latest_decision(self, pair: str, bot_type: BotType) -> Optional[TradingDecision]:
        """
        Obtiene la última decisión para un par y tipo de bot.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            
        Returns:
            Última decisión o None si no existe
        """
        try:
            db = SessionLocal()
            
            try:
                # Buscar la última decisión
                db_decision = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == pair,
                    EstrategiaStatus.estrategia == bot_type.value
                ).order_by(desc(EstrategiaStatus.timestamp)).first()
                
                if db_decision:
                    # Convertir a entidad de dominio
                    decision = self._db_to_domain(db_decision)
                    self.logger.debug(f"✅ Última decisión encontrada para {pair}: {decision.decision.value}")
                    return decision
                else:
                    self.logger.debug(f"ℹ️ No se encontró decisión previa para {pair}")
                    return None
                    
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo última decisión para {pair}: {e}")
            return None
    
    async def get_decisions_history(
        self, 
        pair: str, 
        bot_type: BotType, 
        limit: int = 10
    ) -> List[TradingDecision]:
        """
        Obtiene el historial de decisiones para un par y tipo de bot.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            limit: Número máximo de decisiones a obtener
            
        Returns:
            Lista de decisiones ordenadas por timestamp descendente
        """
        try:
            db = SessionLocal()
            
            try:
                # Buscar decisiones
                db_decisions = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == pair,
                    EstrategiaStatus.estrategia == bot_type.value
                ).order_by(desc(EstrategiaStatus.timestamp)).limit(limit).all()
                
                # Convertir a entidades de dominio
                decisions = [self._db_to_domain(db_decision) for db_decision in db_decisions]
                
                self.logger.debug(f"✅ Historial obtenido para {pair}: {len(decisions)} decisiones")
                return decisions
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo historial para {pair}: {e}")
            return []
    
    async def get_all_latest_decisions(self) -> List[TradingDecision]:
        """
        Obtiene las últimas decisiones para todos los pares.
        
        Returns:
            Lista de últimas decisiones por par
        """
        try:
            db = SessionLocal()
            
            try:
                # Subconsulta para obtener el timestamp más reciente por par y estrategia
                from sqlalchemy import func
                latest_timestamps = db.query(
                    EstrategiaStatus.par,
                    EstrategiaStatus.estrategia,
                    func.max(EstrategiaStatus.timestamp).label('max_timestamp')
                ).group_by(
                    EstrategiaStatus.par,
                    EstrategiaStatus.estrategia
                ).subquery()
                
                # Obtener las últimas decisiones
                db_decisions = db.query(EstrategiaStatus).join(
                    latest_timestamps,
                    (EstrategiaStatus.par == latest_timestamps.c.par) &
                    (EstrategiaStatus.estrategia == latest_timestamps.c.estrategia) &
                    (EstrategiaStatus.timestamp == latest_timestamps.c.max_timestamp)
                ).all()
                
                # Convertir a entidades de dominio
                decisions = [self._db_to_domain(db_decision) for db_decision in db_decisions]
                
                self.logger.debug(f"✅ Últimas decisiones obtenidas: {len(decisions)} decisiones")
                return decisions
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo últimas decisiones: {e}")
            return []
    
    def _db_to_domain(self, db_decision: EstrategiaStatus) -> TradingDecision:
        """
        Convierte un objeto de base de datos a entidad de dominio.
        
        Args:
            db_decision: Objeto de base de datos
            
        Returns:
            Entidad de dominio
        """
        from typing import cast, Any
        
        # Convertir tipo de decisión
        try:
            decision_type = DecisionType(db_decision.decision)
        except ValueError:
            decision_type = DecisionType.ERROR
        
        # Convertir tipo de bot
        try:
            bot_type = BotType(db_decision.estrategia)
        except ValueError:
            bot_type = BotType.GRID
        
        # Crear indicadores - usar type casting para resolver linter
        adx_value = cast(Any, db_decision.adx_actual)
        volatility_value = cast(Any, db_decision.volatilidad_actual)
        sentiment_value = cast(Any, db_decision.sentiment_promedio)
        timestamp_value = cast(Any, db_decision.timestamp)
        
        indicators = MarketIndicators(
            adx=float(adx_value) if adx_value is not None else 0.0,
            volatility=float(volatility_value) if volatility_value is not None else 0.0,
            sentiment=float(sentiment_value) if sentiment_value is not None else None,
            timestamp=timestamp_value
        )
        
        # Crear umbrales - usar type casting para resolver linter
        umbral_adx_value = cast(Any, db_decision.umbral_adx)
        umbral_volatilidad_value = cast(Any, db_decision.umbral_volatilidad)
        umbral_sentimiento_value = cast(Any, db_decision.umbral_sentimiento)
        
        thresholds = TradingThresholds(
            adx_threshold=float(umbral_adx_value) if umbral_adx_value is not None else 0.0,
            volatility_threshold=float(umbral_volatilidad_value) if umbral_volatilidad_value is not None else 0.0,
            sentiment_threshold=float(umbral_sentimiento_value) if umbral_sentimiento_value is not None else 0.0,
            bot_type=bot_type
        )
        
        # Crear decisión - usar type casting para resolver linter
        par_value = cast(Any, db_decision.par)
        razon_value = cast(Any, db_decision.razon)
        
        decision = TradingDecision(
            pair=str(par_value),
            decision=decision_type,
            reason=str(razon_value) if razon_value is not None else "",
            indicators=indicators,
            thresholds=thresholds,
            bot_type=bot_type,
            timestamp=timestamp_value,
            success=True
        )
        
        return decision
    
    async def get_decision_statistics(self, pair: Optional[str] = None, bot_type: Optional[BotType] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de las decisiones.
        
        Args:
            pair: Par específico (opcional)
            bot_type: Tipo de bot específico (opcional)
            
        Returns:
            Estadísticas de decisiones
        """
        try:
            db = SessionLocal()
            
            try:
                query = db.query(EstrategiaStatus)
                
                # Aplicar filtros
                if pair:
                    query = query.filter(EstrategiaStatus.par == pair)
                if bot_type:
                    query = query.filter(EstrategiaStatus.estrategia == bot_type.value)
                
                # Obtener estadísticas
                total_decisions = query.count()
                
                # Decisiones por tipo
                operate_count = query.filter(EstrategiaStatus.decision == DecisionType.OPERATE.value).count()
                pause_count = query.filter(EstrategiaStatus.decision == DecisionType.PAUSE.value).count()
                error_count = query.filter(EstrategiaStatus.decision == DecisionType.ERROR.value).count()
                
                # Última decisión
                latest_decision = query.order_by(desc(EstrategiaStatus.timestamp)).first()
                
                stats = {
                    'total_decisions': total_decisions,
                    'operate_decisions': operate_count,
                    'pause_decisions': pause_count,
                    'error_decisions': error_count,
                    'latest_decision': self._db_to_domain(latest_decision).to_dict() if latest_decision else None
                }
                
                return stats
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {} 