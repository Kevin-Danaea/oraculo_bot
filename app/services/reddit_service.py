import praw
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db import models

logger = get_logger(__name__)

# Lista blanca de dominios de noticias para filtrar
NEWS_DOMAINS = [
    'coindesk.com', 'cointelegraph.com', 'theblockcrypto.com',
    'decrypt.co', 'beincrypto.com', 'reuters.com', 'bloomberg.com',
    'techcrunch.com', 'forbes.com', 'cnbc.com', 'marketwatch.com',
    'ccn.com', 'newsbtc.com', 'cryptoslate.com', 'u.today'
]

def get_reddit_instance():
    """
    Crea y retorna una instancia de Reddit usando las credenciales configuradas.
    """
    try:
        return praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
            check_for_async=False
        )
    except Exception as e:
        logger.error(f"Error al conectar con Reddit: {e}")
        raise

def fetch_and_store_posts(db: Session):
    """
    Obtiene posts de r/CryptoCurrency, los filtra para quedarse solo con noticias
    y los guarda en la base de datos, evitando duplicados.
    """
    try:
        # Verificar credenciales
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("⚠️ No se han configurado las credenciales de Reddit")
            return {"success": False, "error": "Credenciales de Reddit no configuradas"}

        reddit = get_reddit_instance()
        subreddit = reddit.subreddit('CryptoCurrency')
        new_posts_count = 0
        total_processed = 0
        
        logger.info("🔄 Buscando noticias en Reddit r/CryptoCurrency...")
        
        # Buscamos en los 'hot' posts, que suelen tener más relevancia
        for submission in subreddit.hot(limit=25):
            try:
                # Nos aseguramos de que no sea un self-post (solo texto) y que el dominio esté en nuestra lista blanca
                if not submission.is_self and any(domain in submission.url for domain in NEWS_DOMAINS):
                    total_processed += 1
                    
                    # Comprobar si la noticia ya existe por su URL para evitar duplicados
                    existing_post = db.query(models.Noticia).filter(models.Noticia.url == submission.url).first()
                    if not existing_post:
                        # Convertir timestamp de Reddit a datetime
                        published_timestamp = submission.created_utc
                        published_datetime = datetime.fromtimestamp(published_timestamp, tz=timezone.utc)
                        
                        new_post = models.Noticia(
                            source=f"Reddit ({submission.domain})",
                            headline=submission.title,
                            url=submission.url,
                            published_at=published_datetime.isoformat()
                        )
                        db.add(new_post)
                        new_posts_count += 1
                        logger.info(f"📰 Nueva noticia: {submission.title[:50]}...")
                    else:
                        logger.debug(f"🔄 Noticia existente: {submission.title[:30]}...")
                        
            except Exception as e:
                logger.warning(f"⚠️ Error procesando submission: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Recolección de Reddit completada. Se añadieron {new_posts_count} posts nuevos de {total_processed} procesados.")
        
        return {
            "success": True,
            "new_posts": new_posts_count,
            "total_posts": total_processed,
            "message": f"Se añadieron {new_posts_count} posts nuevos"
        }
        
    except Exception as e:
        logger.error(f"💥 Error en fetch_and_store_posts: {e}")
        db.rollback()
        return {"success": False, "error": str(e)} 