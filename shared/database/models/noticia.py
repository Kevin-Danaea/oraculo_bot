"""
Modelo para noticias y análisis de sentimientos.
Utilizado por el servicio de noticias y consultado por otros servicios.
"""
from sqlalchemy import Column, Integer, String, Text, Float
from .base import Base


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
    primary_emotion = Column(String, nullable=True)  # Emoción principal: Euforia, Optimismo, etc.
    news_category = Column(String, nullable=True)    # Categoría: Regulación, Tecnología/Adopción, etc. 