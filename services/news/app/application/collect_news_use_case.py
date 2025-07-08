"""
Caso de uso para recolectar noticias desde fuentes externas.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time

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
    MEJORADO: Con retry logic y mejor manejo de errores de transacción.
    """
    
    def __init__(self, 
                 news_collector: NewsCollector,
                 news_repository: NewsRepository):
        self.news_collector = news_collector
        self.news_repository = news_repository
    
    def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0):
        """
        Ejecuta una operación con reintentos en caso de error.
        
        Args:
            operation: Función a ejecutar
            max_retries: Número máximo de reintentos
            delay: Delay entre reintentos en segundos
            
        Returns:
            Resultado de la operación
        """
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Intento {attempt + 1} falló: {e}. Reintentando en {delay}s...")
                time.sleep(delay)
                delay *= 2  # Backoff exponencial
    
    def _process_single_news(self, raw_data: Dict[str, Any]) -> bool:
        """
        Procesa una sola noticia con manejo de errores robusto.
        
        Args:
            raw_data: Datos crudos de la noticia
            
        Returns:
            True si se procesó exitosamente, False en caso contrario
        """
        try:
            # Verificar si ya existe con retry
            def check_existing():
                return self.news_repository.find_by_url(raw_data['url'])
            
            existing = self._retry_operation(check_existing)
            if existing:
                return False  # Ya existe, no es nueva
            
            # Crear entidad de dominio
            news = News(
                id=None,
                source=raw_data['source'],
                headline=raw_data['headline'],
                url=raw_data['url'],
                published_at=raw_data['published_at']
            )
            
            # Guardar con retry
            def save_news():
                return self.news_repository.save(news)
            
            saved_news = self._retry_operation(save_news)
            headline_text = saved_news.headline[:50] if saved_news and saved_news.headline else 'Sin título'
            logger.info(f"📰 Nueva noticia guardada: {headline_text}...")
            return True
            
        except Exception as e:
            logger.error(f"Error procesando noticia '{raw_data.get('headline', 'Unknown')}': {e}")
            return False
    
    def execute(self) -> CollectNewsResult:
        """
        Ejecuta la recolección de noticias con manejo robusto de errores.
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
            
            logger.info(f"📰 Recolectadas {total_posts} noticias crudas")
            
            # Convertir a entidades de dominio y filtrar duplicados
            new_posts = 0
            filtered_stats = {'duplicate_url': 0, 'error_processing': 0}
            
            for raw_data in raw_news_data:
                try:
                    # Procesar noticia individual
                    if self._process_single_news(raw_data):
                        new_posts += 1
                    else:
                        filtered_stats['duplicate_url'] += 1
                        
                except Exception as e:
                    logger.error(f"Error procesando noticia: {e}")
                    filtered_stats['error_processing'] += 1
                    continue
            
            logger.info(f"✅ Procesamiento completado: {new_posts} nuevas, {filtered_stats['duplicate_url']} duplicadas")
            
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