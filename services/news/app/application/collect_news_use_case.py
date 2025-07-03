"""
Caso de uso para recolectar noticias desde fuentes externas.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import News
from app.domain.interfaces import NewsRepository, NewsCollector
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


@dataclass
class CollectNewsResult:
    """Resultado del caso de uso de recolección de noticias."""
    success: bool
    new_posts: int
    total_posts: int
    filtered_stats: Dict[str, int]
    message: str
    error: Optional[str] = None


class CollectNewsUseCase:
    """
    Caso de uso para recolectar noticias desde fuentes externas.
    """
    
    def __init__(self, 
                 news_collector: NewsCollector,
                 news_repository: NewsRepository):
        self.news_collector = news_collector
        self.news_repository = news_repository
    
    def execute(self) -> CollectNewsResult:
        """
        Ejecuta la recolección de noticias.
        """
        try:
            logger.info("🔄 Iniciando recolección de noticias...")
            
            # Recolectar datos crudos desde la fuente
            raw_news_data = self.news_collector.collect_news()
            total_posts = len(raw_news_data)
            
            if not raw_news_data:
                return CollectNewsResult(
                    success=True,
                    new_posts=0,
                    total_posts=0,
                    filtered_stats={},
                    message="No se encontraron noticias nuevas"
                )
            
            # Convertir a entidades de dominio y filtrar duplicados
            new_posts = 0
            filtered_stats = {'duplicate_url': 0}
            
            for raw_data in raw_news_data:
                try:
                    # Verificar si ya existe
                    existing = self.news_repository.find_by_url(raw_data['url'])
                    if existing:
                        filtered_stats['duplicate_url'] += 1
                        continue
                    
                    # Crear entidad de dominio
                    news = News(
                        id=None,
                        source=raw_data['source'],
                        headline=raw_data['headline'],
                        url=raw_data['url'],
                        published_at=raw_data['published_at']
                    )
                    
                    # Guardar en repositorio
                    self.news_repository.save(news)
                    new_posts += 1
                    
                    logger.info(f"📰 Nueva noticia: {news.headline[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error procesando noticia: {e}")
                    continue
            
            # Agregar estadísticas del collector si están disponibles
            # (la implementación concreta puede proporcionar estadísticas adicionales)
            
            return CollectNewsResult(
                success=True,
                new_posts=new_posts,
                total_posts=total_posts,
                filtered_stats=filtered_stats,
                message=f"Se añadieron {new_posts} noticias nuevas"
            )
            
        except Exception as e:
            logger.error(f"💥 Error en recolección de noticias: {e}")
            return CollectNewsResult(
                success=False,
                new_posts=0,
                total_posts=0,
                filtered_stats={},
                message="Error en recolección",
                error=str(e)
            ) 