# Compatibilidad hacia atrás: importar desde services/news
# TODO: Remover este archivo una vez completada la migración
from services.news.services.cryptopanic_service import fetch_and_store_posts

# Re-exportar para compatibilidad
__all__ = ['fetch_and_store_posts'] 