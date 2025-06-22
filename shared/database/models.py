"""
Modelos de base de datos compartidos entre todos los microservicios.
Define la estructura de tablas para sentimientos y análisis.
"""
from sqlalchemy import Column, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Noticia(Base):
    """
    Modelo para almacenar noticias recopiladas y su análisis de sentimientos.
    Utilizado por el servicio de noticias y consultado por otros servicios.
    """
    __tablename__ = "noticias"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    headline = Column(Text, nullable=False)
    url = Column(String, unique=True, index=True)
    published_at = Column(String, nullable=False)
    sentiment_score = Column(Float, nullable=True)  # Se llenará en fases futuras
    entities = Column(Text, nullable=True)          # Se llenará en fases futuras 