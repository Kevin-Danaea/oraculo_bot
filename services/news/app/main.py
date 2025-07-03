"""
News Worker - Servicio de Noticias con Clean Architecture
Recolecta noticias de Reddit y analiza sentimientos usando una arquitectura limpia.
"""
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends

# Importaciones del dominio e infraestructura
from app.domain.interfaces import NewsRepository, NewsCollector, SentimentAnalyzer, NotificationService
from app.infrastructure.reddit_adapter import RedditNewsCollector
from app.infrastructure.gemini_adapter import GeminiSentimentAnalyzer
from app.infrastructure.database_repository import SqlAlchemyNewsRepository
from app.infrastructure.notification_adapter import TelegramNotificationService
from app.infrastructure.scheduler import NewsScheduler

# Casos de uso
from app.application.collect_news_use_case import CollectNewsUseCase
from app.application.analyze_sentiment_use_case import AnalyzeSentimentUseCase
from app.application.news_pipeline_use_case import NewsPipelineUseCase
from app.application.service_lifecycle_use_case import ServiceLifecycleUseCase

# Configuración y utilidades compartidas
from shared.services.logging_config import setup_logging, get_logger
from shared.database.session import init_database


logger = get_logger(__name__)

# Instancias globales para el ciclo de vida de la aplicación
from typing import Optional
scheduler_instance: Optional[NewsScheduler] = None
repository_instance: Optional[SqlAlchemyNewsRepository] = None


def get_repository() -> NewsRepository:
    """Dependency injection para el repositorio."""
    global repository_instance
    if repository_instance is None:
        repository_instance = SqlAlchemyNewsRepository()
    return repository_instance


def get_news_collector() -> NewsCollector:
    """Dependency injection para el recolector de noticias."""
    return RedditNewsCollector()


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Dependency injection para el analizador de sentimientos."""
    return GeminiSentimentAnalyzer()


def get_notification_service() -> NotificationService:
    """Dependency injection para el servicio de notificaciones."""
    return TelegramNotificationService()


def setup_scheduler() -> NewsScheduler:
    """Configura y retorna el scheduler con todas las dependencias inyectadas."""
    # Crear dependencias
    repository = get_repository()
    news_collector = get_news_collector()
    sentiment_analyzer = get_sentiment_analyzer()
    
    # Crear casos de uso
    collect_news_use_case = CollectNewsUseCase(news_collector, repository)
    analyze_sentiment_use_case = AnalyzeSentimentUseCase(sentiment_analyzer, repository)
    pipeline_use_case = NewsPipelineUseCase(collect_news_use_case, analyze_sentiment_use_case)
    
    # Crear y configurar scheduler
    scheduler = NewsScheduler(pipeline_use_case)
    scheduler.setup()
    
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor del ciclo de vida de la aplicación FastAPI."""
    # Startup
    logger.info("🚀 Iniciando News Worker con Clean Architecture...")
    
    try:
        # Configurar logging
        setup_logging()
        
        # Inicializar base de datos
        logger.info("🗄️ Inicializando base de datos...")
        init_database()
        logger.info("✅ Base de datos inicializada correctamente")
        
        # Configurar e iniciar scheduler
        global scheduler_instance
        scheduler_instance = setup_scheduler()
        scheduler_instance.start()
        
        # Notificar inicio exitoso
        notification_service = get_notification_service()
        lifecycle_use_case = ServiceLifecycleUseCase(notification_service)
        lifecycle_use_case.notify_startup()
        
        logger.info("✅ News Worker iniciado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar News Worker: {e}")
        # Intentar notificar el error
        try:
            notification_service = get_notification_service()
            lifecycle_use_case = ServiceLifecycleUseCase(notification_service)
            lifecycle_use_case.notify_error(str(e))
        except:
            pass
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando News Worker...")
    
    try:
        # Detener scheduler
        if scheduler_instance:
            scheduler_instance.stop()
        
        # Cerrar conexión de base de datos
        if repository_instance:
            repository_instance.close()
        
        logger.info("✅ News Worker cerrado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error al cerrar News Worker: {e}")


# Crear aplicación FastAPI
app = FastAPI(
    title="Oráculo Bot - News Worker",
    version="2.0.0",
    description="Servicio de recolección de noticias y análisis de sentimientos con Clean Architecture",
    lifespan=lifespan
)


# === ENDPOINTS ===

@app.get("/", tags=["Status"])
def read_root() -> Dict[str, Any]:
    """Endpoint básico para verificar que el servicio está activo."""
    return {
        "service": "news-worker",
        "version": "2.0.0",
        "status": "alive",
        "architecture": "clean",
        "description": "Servicio de noticias - Recolección Reddit + Análisis sentimientos"
    }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Health check detallado del servicio."""
    try:
        # Verificar scheduler
        scheduler_running = scheduler_instance.is_running if scheduler_instance else False
        jobs_count = scheduler_instance.get_jobs_count() if scheduler_instance else 0
        
        # Verificar base de datos
        db_healthy = True
        try:
            repository = get_repository()
            # Intenta una operación simple para verificar la conexión
            repository.find_unanalyzed(limit=1)
        except Exception as e:
            db_healthy = False
            logger.error(f"Error verificando salud de BD: {e}")
        
        return {
            "service": "news-worker",
            "status": "healthy" if scheduler_running and db_healthy else "degraded",
            "scheduler": {
                "running": scheduler_running,
                "active_jobs": jobs_count
            },
            "database": {
                "connected": db_healthy
            },
            "features": [
                "📰 Reddit collection from multiple crypto subreddits",
                "🧠 Enriched sentiment analysis (score + emotion + category)",
                "🔄 Unified pipeline for collection and analysis every hour",
                "🏗️ Clean Architecture implementation"
            ]
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "service": "news-worker",
            "status": "error",
            "error": str(e)
        }
 