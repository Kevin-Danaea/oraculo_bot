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
    # Subreddits principales existentes
    'CryptoCurrency', 
    'ethtrader', 
    'Bitcoin', 
    'defi', 
    'altcoin',
    'cryptocurrency',
    'CryptoNews',
    'btc',
    'ethereum',
    # Subreddits adicionales agregados
    'bitcoin',  # Bitcoin en minúsculas
    'Ethereum',  # Ethereum con mayúscula
    'DeFi',  # DeFi con mayúscula
    'CryptoMoonShots',
    'cryptomoonshots',
    'SatoshiStreetBets',
    'CryptoCurrencyTrading',
    'CryptoMarkets',
    'Crypto_com',
    'binance',
    'Coinbase',
    'dogecoin',
    'litecoin',
    'ripple',
    'cardano'
]

# Lista blanca de dominios de noticias para filtrar
NEWS_DOMAINS = [
    # Dominios existentes
    'coindesk.com', 'cointelegraph.com', 'theblockcrypto.com',
    'decrypt.co', 'beincrypto.com', 'reuters.com', 'bloomberg.com',
    'techcrunch.com', 'forbes.com', 'cnbc.com', 'marketwatch.com',
    'ccn.com', 'newsbtc.com', 'cryptoslate.com', 'u.today',
    'coinpaprika.com', 'cryptobriefing.com', 'ambcrypto.com',
    'coingape.com', 'zycrypto.com',
    # Dominios adicionales agregados
    'wsj.com', 'ft.com', 'coinbase.com', 'kraken.com', 'crypto.com'
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

# Funciones de filtrado (basadas en procesador_historico.py)
def _filter_basic_quality(submission) -> bool:
    """Filtra por calidad básica del post."""
    # Verificar que el selftext no esté eliminado
    if hasattr(submission, 'selftext'):
        selftext = getattr(submission, 'selftext', '').strip()
        if selftext in ['[deleted]', '[removed]']:
            return False
    
    # Filtrar posts fijados (stickied)
    if getattr(submission, 'stickied', False):
        return False
    
    return True

def _filter_minimum_engagement(submission, min_score: int = 6) -> bool:
    """Filtra por engagement mínimo."""
    score = getattr(submission, 'score', 0)
    return score >= min_score

def _is_trusted_domain(url: str) -> bool:
    """Verifica si el dominio está en la lista blanca."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        # Remover 'www.' si existe
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain in NEWS_DOMAINS
    except Exception:
        return False

def _extract_text_to_analyze(submission) -> tuple:
    """
    Extrae el texto a analizar según el tipo de post.
    
    Returns:
        tuple: (text_to_analyze, post_type, url_to_store)
            - text_to_analyze: El texto para análisis de sentimiento
            - post_type: 'news_link' o 'community_post'
            - url_to_store: URL a guardar en la BD
    """
    title = getattr(submission, 'title', '').strip()
    is_self = getattr(submission, 'is_self', False)
    
    if is_self:
        # Post de texto de la comunidad
        selftext = getattr(submission, 'selftext', '').strip()
        if len(selftext) > 150:  # Solo procesar posts con contenido sustancial
            combined_text = f"{title} {selftext}"
            # URL para self posts
            permalink = getattr(submission, 'permalink', '')
            post_url = f"https://reddit.com{permalink}" if permalink else f"https://reddit.com/r/{submission.subreddit}/comments/{submission.id}"
            return combined_text, 'community_post', post_url
        return None, None, None
    else:
        # Post de enlace (noticia)
        url = getattr(submission, 'url', '')
        if _is_trusted_domain(url):
            return title, 'news_link', url
        return None, None, None

def fetch_and_store_posts(db: Session):
    """
    Obtiene posts de múltiples subreddits de criptomonedas, procesa tanto noticias 
    como posts de la comunidad aplicando filtros de calidad y engagement.
    """
    try:
        # Verificar credenciales
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("⚠️ No se han configurado las credenciales de Reddit")
            return {"success": False, "error": "Credenciales de Reddit no configuradas"}

        reddit = get_reddit_instance()
        new_posts_count = 0
        total_processed = 0
        filtered_stats = {
            'low_quality': 0,
            'low_engagement': 0,
            'short_text': 0,
            'bad_link': 0,
            'duplicate_url': 0
        }
        processed_urls = set()  # Set para evitar duplicados durante esta ejecución
        
        logger.info(f"🔄 Buscando noticias y posts de comunidad en {len(CRYPTO_SUBREDDITS)} subreddits...")
        
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
                            total_processed += 1
                            
                            # FILTRO 1: Calidad básica
                            if not _filter_basic_quality(submission):
                                filtered_stats['low_quality'] += 1
                                continue
                            
                            # FILTRO 2: Engagement mínimo (6 para posts de comunidad)
                            if not _filter_minimum_engagement(submission, min_score=6):
                                filtered_stats['low_engagement'] += 1
                                continue
                            
                            # FILTRO 3: Extraer texto a analizar
                            text_to_analyze, post_type_result, url_to_store = _extract_text_to_analyze(submission)
                            
                            if not text_to_analyze:
                                if getattr(submission, 'is_self', False):
                                    filtered_stats['short_text'] += 1
                                else:
                                    filtered_stats['bad_link'] += 1
                                continue
                            
                            # FILTRO 4: Verificar duplicados
                            if url_to_store in processed_urls:
                                filtered_stats['duplicate_url'] += 1
                                logger.debug(f"🔄 URL duplicada en esta ejecución: {url_to_store}")
                                continue
                                
                            # Verificar duplicados en la base de datos
                            existing_post = db.query(models.Noticia).filter(
                                models.Noticia.url == url_to_store
                            ).first()
                            
                            if not existing_post:
                                # Convertir timestamp de Reddit a datetime
                                published_timestamp = getattr(submission, 'created_utc', 0)
                                published_datetime = datetime.fromtimestamp(published_timestamp, tz=timezone.utc)
                                
                                # Crear registro con información del tipo de post
                                source_info = f"Reddit r/{subreddit_name}"
                                if post_type_result == 'news_link':
                                    source_info += f" ({getattr(submission, 'domain', 'unknown')})"
                                elif post_type_result == 'community_post':
                                    source_info += " (Community Post)"
                                
                                new_post = models.Noticia(
                                    source=source_info,
                                    headline=text_to_analyze,
                                    url=url_to_store,
                                    published_at=published_datetime.isoformat()
                                )
                                db.add(new_post)
                                new_posts_count += 1
                                processed_urls.add(url_to_store)  # Marcar como procesada
                                
                                # Log diferenciado por tipo
                                if post_type_result == 'news_link':
                                    logger.info(f"📰 Nueva noticia de r/{subreddit_name}: {submission.title[:50]}...")
                                else:
                                    logger.info(f"💬 Nuevo post de comunidad de r/{subreddit_name}: {submission.title[:50]}...")
                            else:
                                filtered_stats['duplicate_url'] += 1
                                logger.debug(f"🔄 Post existente en BD: {submission.title[:30]}...")
                                processed_urls.add(url_to_store)  # Marcar para evitar reprocesamiento
                                    
                        except Exception as e:
                            logger.warning(f"⚠️ Error procesando submission en r/{subreddit_name}: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"💥 Error procesando subreddit r/{subreddit_name}: {e}")
                continue
        
        db.commit()
        
        # Log estadísticas detalladas
        logger.info(f"✅ Recolección de Reddit completada:")
        logger.info(f"   📊 Posts nuevos añadidos: {new_posts_count}")
        logger.info(f"   🔍 Posts procesados: {total_processed}")
        logger.info(f"   📱 Subreddits consultados: {len(CRYPTO_SUBREDDITS)}")
        logger.info(f"   🚫 Filtrados:")
        logger.info(f"      - Baja calidad: {filtered_stats['low_quality']}")
        logger.info(f"      - Bajo engagement: {filtered_stats['low_engagement']}")
        logger.info(f"      - Texto insuficiente: {filtered_stats['short_text']}")
        logger.info(f"      - Dominio no confiable: {filtered_stats['bad_link']}")
        logger.info(f"      - URLs duplicadas: {filtered_stats['duplicate_url']}")
        
        return {
            "success": True,
            "new_posts": new_posts_count,
            "total_posts": total_processed,
            "subreddits_processed": len(CRYPTO_SUBREDDITS),
            "filtered_stats": filtered_stats,
            "message": f"Se añadieron {new_posts_count} posts (noticias y comunidad) desde {len(CRYPTO_SUBREDDITS)} subreddits"
        }
        
    except Exception as e:
        logger.error(f"💥 Error en fetch_and_store_posts: {e}")
        db.rollback()
        return {"success": False, "error": str(e)} 