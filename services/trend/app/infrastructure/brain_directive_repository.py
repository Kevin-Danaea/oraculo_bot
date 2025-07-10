"""Repository for getting brain directives from database."""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..domain.entities import BrainDirective, BrainDecision
from ..domain.interfaces import IBrainDirectiveRepository
from shared.database.models import EstrategiaStatus
from shared.database.session import SessionLocal

logger = logging.getLogger(__name__)


class DatabaseBrainDirectiveRepository(IBrainDirectiveRepository):
    """Implementación del repositorio de directivas del cerebro usando base de datos."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_latest_directive(self, symbol: str) -> Optional[BrainDirective]:
        """
        Obtiene la última directiva del cerebro para un símbolo.
        
        Args:
            symbol: Símbolo de trading (ej: "BTCUSDT")
            
        Returns:
            BrainDirective si se encuentra, None en caso contrario
        """
        try:
            db = SessionLocal()
            
            try:
                # Buscar la última directiva para el símbolo y estrategia TREND
                latest_directive = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == symbol,
                    EstrategiaStatus.estrategia == "TREND"
                ).order_by(desc(EstrategiaStatus.timestamp)).first()
                
                if not latest_directive:
                    self.logger.debug(f"No se encontró directiva para {symbol}")
                    return None
                
                # Convertir a entidad de dominio
                brain_directive = self._db_to_domain(latest_directive)
                
                self.logger.debug(
                    f"Directiva encontrada para {symbol}: {brain_directive.decision.value}"
                )
                
                return brain_directive
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error obteniendo directiva del cerebro: {e}")
            return None
    
    def _db_to_domain(self, db_directive: EstrategiaStatus) -> BrainDirective:
        """
        Convierte un objeto de base de datos a entidad de dominio.
        
        Args:
            db_directive: Objeto de base de datos
            
        Returns:
            Entidad de dominio
        """
        # Mapear decisión de la base de datos a BrainDecision
        decision_mapping = {
            "INICIAR_COMPRA_TENDENCIA": BrainDecision.INICIAR_COMPRA_TENDENCIA,
            "MANTENER_POSICION": BrainDecision.MANTENER_POSICION,
            "CERRAR_POSICION": BrainDecision.CERRAR_POSICION,
        }
        
        decision = decision_mapping.get(
            str(db_directive.decision), 
            BrainDecision.MANTENER_POSICION
        )
        
        # Crear indicadores si están disponibles
        indicators = {}
        adx_value = getattr(db_directive, 'adx_actual', None)
        volatility_value = getattr(db_directive, 'volatilidad_actual', None)
        sentiment_value = getattr(db_directive, 'sentiment_promedio', None)
        
        if adx_value is not None:
            indicators["adx"] = float(adx_value)
        if volatility_value is not None:
            indicators["volatility"] = float(volatility_value)
        if sentiment_value is not None:
            indicators["sentiment"] = float(sentiment_value)
        
        return BrainDirective(
            symbol=str(db_directive.par),
            decision=decision,
            timestamp=getattr(db_directive, 'timestamp', datetime.utcnow()),
            reason=str(db_directive.razon) if getattr(db_directive, 'razon', None) else None,
            indicators=indicators if indicators else None
        ) 