# Compatibilidad hacia atrás: importar desde services/news
# TODO: Remover este archivo una vez completada la migración
from services.news.schedulers.news_scheduler import (
    setup_news_scheduler,
    start_news_scheduler,
    stop_news_scheduler,
    run_collection_job,
    run_sentiment_analysis_job
)

# Crear scheduler con compatibilidad hacia atrás
scheduler = setup_news_scheduler()

# Re-exportar para compatibilidad
__all__ = [
    'scheduler',
    'run_collection_job', 
    'run_sentiment_analysis_job'
] 