"""
Adaptador de infraestructura para la base de datos.
Implementa la interfaz HypeRepository para interactuar con la BD.
"""
from typing import List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from shared.database import models
from shared.services.logging_config import get_logger
from app.domain.entities import HypeEvent, HypeScan
from app.domain.interfaces import HypeRepository

logger = get_logger(__name__)

class DatabaseHypeRepository(HypeRepository):
    """
    Implementación del repositorio de Hype que usa SQLAlchemy para la persistencia.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def save_scan(self, scan_data: HypeScan) -> HypeScan:
        """
        Guarda el resultado de un escaneo completo, incluyendo el escaneo principal
        y todas sus menciones asociadas.
        """
        try:
            db_scan = models.HypeScan(
                scan_timestamp=scan_data.scan_timestamp,
                subreddits_scanned=scan_data.subreddits_scanned,
                posts_analyzed=scan_data.posts_analyzed,
                tickers_mentioned=scan_data.unique_tickers_mentioned
            )
            self.db.add(db_scan)
            self.db.flush()

            scan_id = db_scan.id # type: ignore
            if scan_id is None:
                raise ValueError("No se pudo obtener el ID del HypeScan guardado.")

            for mention in scan_data.mentions:
                db_mention = models.HypeMention(
                    scan_id=scan_id,
                    ticker=mention.ticker,
                    mention_count=mention.count
                )
                self.db.add(db_mention)
            
            self.db.commit()
            scan_data.id = scan_id # type: ignore
            logger.info(f"💾 Resultados del escaneo guardados en la BD (Scan ID: {scan_id})")
            return scan_data
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error guardando resultados del Hype Radar en BD: {e}")
            raise

    def save_event(self, event_data: HypeEvent) -> HypeEvent:
        """
        Guarda un evento de Hype (alerta) en la base de datos.
        """
        try:
            db_event = models.HypeEvent(
                ticker=event_data.ticker,
                mentions_24h=event_data.mentions_24h,
                threshold=event_data.threshold,
                alert_sent=event_data.alert_sent,
                timestamp=event_data.timestamp
            )
            self.db.add(db_event)
            self.db.commit()
            self.db.refresh(db_event)
            
            event_data.id = db_event.id # type: ignore
            logger.info(f"💾 Evento de Hype guardado en BD: ${event_data.ticker} (ID: {db_event.id})")
            return event_data
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error guardando evento de Hype en BD: {e}")
            raise

    def get_recent_events(self, hours: int, limit: int) -> List[HypeEvent]:
        """
        Obtiene los eventos de Hype (alertas) más recientes de la base de datos.
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            db_events = self.db.query(models.HypeEvent)\
                .filter(models.HypeEvent.timestamp >= cutoff_time)\
                .order_by(models.HypeEvent.timestamp.desc())\
                .limit(limit)\
                .all()
            
            return [
                HypeEvent(
                    id=event.id, # type: ignore
                    ticker=str(event.ticker), # type: ignore
                    mentions_24h=int(event.mentions_24h), # type: ignore
                    threshold=int(event.threshold), # type: ignore
                    alert_sent=bool(event.alert_sent), # type: ignore
                    timestamp=event.timestamp # type: ignore
                ) for event in db_events
            ]
        except Exception as e:
            logger.error(f"❌ Error obteniendo eventos de Hype de BD: {e}")
            return [] 