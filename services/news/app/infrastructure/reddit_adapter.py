"""
Adaptador de Reddit para recolectar noticias.
Implementación concreta de la interfaz NewsCollector.
"""
import praw
from datetime import datetime, timezone
from typing import List, Dict, Any
from urllib.parse import urlparse

from app.domain.interfaces import NewsCollector
from shared.config.settings import settings
from shared.services.logging_config import get_logger


logger = get_logger(__name__)


class RedditNewsCollector(NewsCollector):
    """
    Implementación del recolector de noticias usando Reddit API.
    """
    
    # Lista de subreddits relacionados con criptomonedas
    CRYPTO_SUBREDDITS = [
        # Subreddits principales
        'CryptoCurrency', 'ethtrader', 'Bitcoin', 'defi', 'altcoin',
        'cryptocurrency', 'CryptoNews', 'btc', 'ethereum',
        # Subreddits adicionales
        'bitcoin', 'Ethereum', 'DeFi', 'CryptoMoonShots', 'cryptomoonshots',
        'SatoshiStreetBets', 'CryptoCurrencyTrading', 'CryptoMarkets',
        'Crypto_com', 'binance', 'Coinbase', 'dogecoin', 'litecoin',
        'ripple', 'cardano'
    ]
    
    # Lista blanca de dominios de noticias
    NEWS_DOMAINS = [
        # Dominios principales
        'coindesk.com', 'cointelegraph.com', 'theblockcrypto.com',
        'decrypt.co', 'beincrypto.com', 'reuters.com', 'bloomberg.com',
        'techcrunch.com', 'forbes.com', 'cnbc.com', 'marketwatch.com',
        'ccn.com', 'newsbtc.com', 'cryptoslate.com', 'u.today',
        'coinpaprika.com', 'cryptobriefing.com', 'ambcrypto.com',
        'coingape.com', 'zycrypto.com',
        # Dominios adicionales
        'wsj.com', 'ft.com', 'coinbase.com', 'kraken.com', 'crypto.com'
    ]
    
    def __init__(self):
        self._reddit = None
        self._filtered_stats = {
            'low_quality': 0,
            'low_engagement': 0,
            'short_text': 0,
            'bad_link': 0
        }
    
    def _get_reddit_instance(self) -> praw.Reddit:
        """Obtiene o crea una instancia de Reddit."""
        if self._reddit is None:
            if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
                raise ValueError("Credenciales de Reddit no configuradas")
            
            self._reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                check_for_async=False
            )
        return self._reddit
    
    def _filter_basic_quality(self, submission) -> bool:
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
    
    def _filter_minimum_engagement(self, submission, min_score: int = 6) -> bool:
        """Filtra por engagement mínimo."""
        score = getattr(submission, 'score', 0)
        return score >= min_score
    
    def _is_trusted_domain(self, url: str) -> bool:
        """Verifica si el dominio está en la lista blanca."""
        try:
            domain = urlparse(url).netloc.lower()
            # Remover 'www.' si existe
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain in self.NEWS_DOMAINS
        except Exception:
            return False
    
    def _extract_text_to_analyze(self, submission) -> tuple:
        """
        Extrae el texto a analizar según el tipo de post.
        
        Returns:
            tuple: (text_to_analyze, post_type, url_to_store)
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
            if self._is_trusted_domain(url):
                return title, 'news_link', url
            return None, None, None
    
    def collect_news(self) -> List[Dict[str, Any]]:
        """
        Recolecta noticias desde Reddit.
        
        Returns:
            Lista de diccionarios con datos de noticias.
        """
        logger.info(f"🔄 Buscando noticias en {len(self.CRYPTO_SUBREDDITS)} subreddits...")
        
        # Resetear estadísticas
        self._filtered_stats = {
            'low_quality': 0,
            'low_engagement': 0,
            'short_text': 0,
            'bad_link': 0
        }
        
        reddit = self._get_reddit_instance()
        collected_news = []
        processed_urls = set()  # Para evitar duplicados durante esta ejecución
        
        for subreddit_name in self.CRYPTO_SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                logger.info(f"📱 Procesando r/{subreddit_name}...")
                
                # Procesar posts 'hot' y 'new'
                post_types = [
                    ('hot', subreddit.hot(limit=15)),
                    ('new', subreddit.new(limit=10))
                ]
                
                for post_type, submissions in post_types:
                    logger.debug(f"🔍 Procesando posts '{post_type}' de r/{subreddit_name}")
                    
                    for submission in submissions:
                        try:
                            # FILTRO 1: Calidad básica
                            if not self._filter_basic_quality(submission):
                                self._filtered_stats['low_quality'] += 1
                                continue
                            
                            # FILTRO 2: Engagement mínimo
                            if not self._filter_minimum_engagement(submission):
                                self._filtered_stats['low_engagement'] += 1
                                continue
                            
                            # FILTRO 3: Extraer texto a analizar
                            text_to_analyze, post_type_result, url_to_store = self._extract_text_to_analyze(submission)
                            
                            if not text_to_analyze:
                                if getattr(submission, 'is_self', False):
                                    self._filtered_stats['short_text'] += 1
                                else:
                                    self._filtered_stats['bad_link'] += 1
                                continue
                            
                            # FILTRO 4: Verificar duplicados en esta ejecución
                            if url_to_store in processed_urls:
                                continue
                            
                            # Convertir timestamp a datetime
                            published_timestamp = getattr(submission, 'created_utc', 0)
                            published_datetime = datetime.fromtimestamp(published_timestamp, tz=timezone.utc)
                            
                            # Crear información de fuente
                            source_info = f"Reddit r/{subreddit_name}"
                            if post_type_result == 'news_link':
                                source_info += f" ({getattr(submission, 'domain', 'unknown')})"
                            elif post_type_result == 'community_post':
                                source_info += " (Community Post)"
                            
                            # Agregar a la colección
                            news_data = {
                                'source': source_info,
                                'headline': text_to_analyze,
                                'url': url_to_store,
                                'published_at': published_datetime
                            }
                            
                            collected_news.append(news_data)
                            processed_urls.add(url_to_store)
                            
                            # Log diferenciado por tipo
                            if post_type_result == 'news_link':
                                logger.debug(f"📰 Noticia recolectada de r/{subreddit_name}: {submission.title[:50]}...")
                            else:
                                logger.debug(f"💬 Post de comunidad recolectado de r/{subreddit_name}: {submission.title[:50]}...")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error procesando submission en r/{subreddit_name}: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"💥 Error procesando subreddit r/{subreddit_name}: {e}")
                continue
        
        # Log estadísticas
        logger.info(f"✅ Recolección de Reddit completada:")
        logger.info(f"   📊 Posts recolectados: {len(collected_news)}")
        logger.info(f"   📱 Subreddits consultados: {len(self.CRYPTO_SUBREDDITS)}")
        logger.info(f"   🚫 Filtrados:")
        logger.info(f"      - Baja calidad: {self._filtered_stats['low_quality']}")
        logger.info(f"      - Bajo engagement: {self._filtered_stats['low_engagement']}")
        logger.info(f"      - Texto insuficiente: {self._filtered_stats['short_text']}")
        logger.info(f"      - Dominio no confiable: {self._filtered_stats['bad_link']}")
        
        return collected_news
    
    def get_filtered_stats(self) -> Dict[str, int]:
        """Obtiene las estadísticas de filtrado."""
        return self._filtered_stats.copy() 