"""
Servicio de Reddit para recopilación de noticias de criptomonedas.
Migrado desde app/services/reddit_service.py manteniendo funcionalidad exacta.
"""
import praw
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared.config.settings import settings
from shared.services.logging_config import get_logger
from shared.database import models

logger = get_logger(__name__)

# Lista de subreddits relacionados con criptomonedas para consultar
CRYPTO_SUBREDDITS = [
    'CryptoCurrency', 
    'ethtrader', 
    'Bitcoin', 
    'defi', 
    'altcoin',
    'cryptocurrency',
    'CryptoNews',
    'btc',
    'ethereum'
]

# Lista blanca de dominios de noticias para filtrar
NEWS_DOMAINS = [
    'coindesk.com', 'cointelegraph.com', 'theblockcrypto.com',
    'decrypt.co', 'beincrypto.com', 'reuters.com', 'bloomberg.com',
    'techcrunch.com', 'forbes.com', 'cnbc.com', 'marketwatch.com',
    'ccn.com', 'newsbtc.com', 'cryptoslate.com', 'u.today',
    'coinpaprika.com', 'cryptobriefing.com', 'ambcrypto.com',
    'coingape.com', 'zycrypto.com'
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
    Obtiene posts de múltiples subreddits de criptomonedas, consulta tanto 'hot' como 'new',
    los filtra para quedarse solo con noticias y los guarda en la base de datos, 
    evitando duplicados por URL.
    """
    try:
        # Verificar credenciales
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("⚠️ No se han configurado las credenciales de Reddit")
            return {"success": False, "error": "Credenciales de Reddit no configuradas"}

        reddit = get_reddit_instance()
        new_posts_count = 0
        total_processed = 0
        processed_urls = set()  # Set para evitar duplicados durante esta ejecución
        
        logger.info(f"🔄 Buscando noticias en {len(CRYPTO_SUBREDDITS)} subreddits...")
        
        # Iterar sobre cada subreddit
        for subreddit_name in CRYPTO_SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                logger.info(f"📱 Procesando r/{subreddit_name}...")
                
                # Procesar posts 'hot' y 'new' para mayor cobertura
                post_types = [
                    ('hot', subreddit.hot(limit=15)),  # 15 posts hot por subreddit
                    ('new', subreddit.new(limit=10))   # 10 posts new por subreddit
                ]
                
                for post_type, submissions in post_types:
                    logger.debug(f"🔍 Procesando posts '{post_type}' de r/{subreddit_name}")
                    
                    for submission in submissions:
                        try:
                            # Filtrar: no self-posts, debe tener dominio de noticias
                            if not submission.is_self and any(domain in submission.url for domain in NEWS_DOMAINS):
                                total_processed += 1
                                
                                # Verificar duplicados en esta ejecución
                                if submission.url in processed_urls:
                                    logger.debug(f"🔄 URL duplicada en esta ejecución: {submission.url}")
                                    continue
                                
                                # Verificar duplicados en la base de datos
                                existing_post = db.query(models.Noticia).filter(
                                    models.Noticia.url == submission.url
                                ).first()
                                
                                if not existing_post:
                                    # Convertir timestamp de Reddit a datetime
                                    published_timestamp = submission.created_utc
                                    published_datetime = datetime.fromtimestamp(published_timestamp, tz=timezone.utc)
                                    
                                    new_post = models.Noticia(
                                        source=f"Reddit r/{subreddit_name} ({submission.domain})",
                                        headline=submission.title,
                                        url=submission.url,
                                        published_at=published_datetime.isoformat()
                                    )
                                    db.add(new_post)
                                    new_posts_count += 1
                                    processed_urls.add(submission.url)  # Marcar como procesada
                                    logger.info(f"📰 Nueva noticia de r/{subreddit_name}: {submission.title[:50]}...")
                                else:
                                    logger.debug(f"🔄 Noticia existente en BD: {submission.title[:30]}...")
                                    processed_urls.add(submission.url)  # Marcar para evitar reprocesamiento
                                    
                        except Exception as e:
                            logger.warning(f"⚠️ Error procesando submission en r/{subreddit_name}: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"💥 Error procesando subreddit r/{subreddit_name}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Recolección de Reddit completada. Se añadieron {new_posts_count} posts nuevos de {total_processed} procesados desde {len(CRYPTO_SUBREDDITS)} subreddits.")
        
        return {
            "success": True,
            "new_posts": new_posts_count,
            "total_posts": total_processed,
            "subreddits_processed": len(CRYPTO_SUBREDDITS),
            "message": f"Se añadieron {new_posts_count} posts nuevos desde {len(CRYPTO_SUBREDDITS)} subreddits"
        }
        
    except Exception as e:
        logger.error(f"💥 Error en fetch_and_store_posts: {e}")
        db.rollback()
        return {"success": False, "error": str(e)} 