"""
Modelos para el sistema de escaneo de hype.
Registra ejecuciones del Hype Radar y las menciones detectadas.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class HypeScan(Base):
    """
    Registra una ejecución del escaneo del Hype Radar.
    """
    __tablename__ = 'hype_scans'
    
    id = Column(Integer, primary_key=True, index=True)
    scan_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    subreddits_scanned = Column(Integer)
    posts_analyzed = Column(Integer)
    tickers_mentioned = Column(Integer)
    
    # Relación uno a muchos con las menciones
    mentions = relationship("HypeMention", back_populates="scan")


class HypeMention(Base):
    """
    Registra las menciones de un ticker específico en un escaneo.
    """
    __tablename__ = 'hype_mentions'
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey('hype_scans.id'))
    ticker = Column(String, index=True)
    mention_count = Column(Integer)
    
    # Relación muchos a uno con el escaneo
    scan = relationship("HypeScan", back_populates="mentions") 