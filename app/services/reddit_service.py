# Compatibilidad hacia atrás: importar desde services/news
# TODO: Remover este archivo una vez completada la migración
from services.news.services.reddit_service import (
    get_reddit_instance,
    fetch_and_store_posts,
    NEWS_DOMAINS
)

# Re-exportar para compatibilidad
__all__ = [
    'get_reddit_instance',
    'fetch_and_store_posts', 
    'NEWS_DOMAINS'
] 