"""
Repositorio de base de datos para noticias.
Implementación concreta de la interfaz NewsRepository.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from contextlib import contextmanager

from app.domain.interfaces import NewsRepository
from app.domain.entities import News, SentimentAnalysis, EmotionType, CategoryType
from shared.database.models import Noticia as NoticiaModel
from shared.database.session import SessionLocal
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class SqlAlchemyNewsRepository(NewsRepository):
    """
    Implementación del repositorio de noticias usando SQLAlchemy.
    MEJORADO: Manejo correcto de sesiones para evitar errores de transacción.
    """
    
    def __init__(self):
        # Ya no mantenemos una sesión global
        pass
    
    @contextmanager
    def _get_session(self):
        """
        Context manager para obtener una sesión de base de datos.
        Maneja automáticamente commit, rollback y cierre de sesión.
        """
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Error en transacción de BD: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def _model_to_entity(self, model: NoticiaModel) -> News:
        """Convierte un modelo de base de datos a una entidad del dominio."""
        # Convertir strings a enums si están presentes
        primary_emotion = None
        if model.primary_emotion is not None:
            try:
                primary_emotion = EmotionType(str(model.primary_emotion))
            except ValueError:
                logger.warning(f"Emoción inválida en BD: {model.primary_emotion}")
        
        news_category = None
        if model.news_category is not None:
            try:
                news_category = CategoryType(str(model.news_category))
            except ValueError:
                logger.warning(f"Categoría inválida en BD: {model.news_category}")
        
        # Parsear fecha
        from datetime import datetime
        published_at_str = str(model.published_at)
        if isinstance(model.published_at, str):
            published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
        else:
            published_at = model.published_at
        
        return News(
            id=model.id,  # type: ignore
            source=model.source,  # type: ignore
            headline=model.headline,  # type: ignore
            url=model.url,  # type: ignore
            published_at=published_at,  # type: ignore
            sentiment_score=model.sentiment_score,  # type: ignore
            primary_emotion=primary_emotion,
            news_category=news_category
        )
    
    def _entity_to_model(self, entity: News) -> NoticiaModel:
        """Convierte una entidad del dominio a un modelo de base de datos."""
        return NoticiaModel(
            source=entity.source,
            headline=entity.headline,
            url=entity.url,
            published_at=entity.published_at.isoformat(),
            sentiment_score=entity.sentiment_score,
            primary_emotion=entity.primary_emotion.value if entity.primary_emotion else None,
            news_category=entity.news_category.value if entity.news_category else None
        )
    
    def save(self, news: News) -> News:
        """
        Guarda una noticia en la base de datos.
        
        Args:
            news: Entidad de noticia a guardar
            
        Returns:
            Noticia guardada con ID asignado
        """
        with self._get_session() as session:
            try:
                # Convertir a modelo
                model = self._entity_to_model(news)
                
                # Guardar
                session.add(model)
                session.flush()  # Para obtener el ID
                
                # Retornar con ID asignado
                news.id = model.id  # type: ignore
                logger.debug(f"✅ Noticia guardada con ID: {news.id}")
                return news
                
            except Exception as e:
                logger.error(f"Error guardando noticia: {e}")
                raise
    
    def save_many(self, news_list: List[News]) -> List[News]:
        """
        Guarda múltiples noticias de forma eficiente.
        
        Args:
            news_list: Lista de noticias a guardar
            
        Returns:
            Lista de noticias guardadas con IDs asignados
        """
        with self._get_session() as session:
            try:
                models = [self._entity_to_model(news) for news in news_list]
                session.bulk_save_objects(models, return_defaults=True)
                session.flush()  # Para obtener los IDs
                
                # Actualizar IDs en las entidades
                for news, model in zip(news_list, models):
                    news.id = model.id  # type: ignore
                
                logger.debug(f"✅ {len(news_list)} noticias guardadas en lote")
                return news_list
                
            except Exception as e:
                logger.error(f"Error guardando múltiples noticias: {e}")
                raise
    
    def find_by_url(self, url: str) -> Optional[News]:
        """
        Busca una noticia por su URL.
        
        Args:
            url: URL de la noticia
            
        Returns:
            Noticia encontrada o None
        """
        with self._get_session() as session:
            try:
                model = session.query(NoticiaModel).filter(
                    NoticiaModel.url == url
                ).first()
                
                if model:
                    return self._model_to_entity(model)
                return None
                
            except Exception as e:
                logger.error(f"Error buscando noticia por URL: {e}")
                raise
    
    def find_unanalyzed(self, limit: int = 500) -> List[News]:
        """
        Obtiene noticias que no han sido analizadas.
        
        Args:
            limit: Número máximo de noticias a retornar
            
        Returns:
            Lista de noticias sin analizar
        """
        with self._get_session() as session:
            try:
                models = session.query(NoticiaModel).filter(
                    NoticiaModel.sentiment_score == None
                ).limit(limit).all()
                
                result = [self._model_to_entity(model) for model in models]
                logger.debug(f"✅ Encontradas {len(result)} noticias sin analizar")
                return result
                
            except Exception as e:
                logger.error(f"Error obteniendo noticias sin analizar: {e}")
                raise
    
    def update_sentiment_analysis(self, news_id: int, analysis: SentimentAnalysis) -> News:
        """
        Actualiza el análisis de sentimiento de una noticia.
        
        Args:
            news_id: ID de la noticia
            analysis: Análisis de sentimiento
            
        Returns:
            Noticia actualizada
        """
        with self._get_session() as session:
            try:
                model = session.query(NoticiaModel).filter(
                    NoticiaModel.id == news_id
                ).first()
                
                if not model:
                    raise ValueError(f"Noticia con ID {news_id} no encontrada")
                
                # Actualizar campos de análisis
                model.sentiment_score = analysis.sentiment_score  # type: ignore
                model.primary_emotion = analysis.primary_emotion.value  # type: ignore
                model.news_category = analysis.news_category.value  # type: ignore
                
                logger.debug(f"✅ Análisis actualizado para noticia ID: {news_id}")
                return self._model_to_entity(model)
                
            except Exception as e:
                logger.error(f"Error actualizando análisis de sentimiento: {e}")
                raise
    
    def close(self):
        """Cierra la sesión de base de datos. Ya no es necesario con el nuevo enfoque."""
        logger.debug("✅ Repositorio cerrado (no hay sesión global que cerrar)")
        pass 