"""
Adaptador de infraestructura para coleccionar datos de Hype desde Reddit.
"""
import praw
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from shared.config.settings import settings
from shared.services.logging_config import get_logger
from app.domain.entities import Post
from app.domain.interfaces import HypeCollector

logger = get_logger(__name__)

# Lista de tickers de memecoins y altcoins populares para monitorear
# Esta lista ayuda a la función `extract_tickers_from_text` a ser más precisa.
TARGET_TICKERS = [
    'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'BOME', 'ADA', 'DOT', 
    'LINK', 'UNI', 'AVAX', 'MATIC', 'ATOM', 'LTC', 'BCH', 'XRP', 'TRX', 
    'VET', 'ALGO', 'HBAR', 'AAVE', 'COMP', 'MKR', 'SNX', 'YFI', 'SUSHI', 
    '1INCH', 'SOL', 'APT', 'SUI', 'ARB', 'OP', 'BLUR', 'ID'
]

class RedditHypeCollector(HypeCollector):
    """Implementación de HypeCollector que usa la API de Reddit."""

    def __init__(self):
        """Inicializa el colector con una instancia de PRAW."""
        self.reddit = self._get_reddit_instance()
        if not self.reddit:
            raise ConnectionError("No se pudo establecer conexión con Reddit. Verifica las credenciales.")

    def _get_reddit_instance(self):
        """
        Crea y retorna una instancia de Reddit usando las credenciales configuradas.
        """
        try:
            if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
                logger.warning("⚠️ No se han configurado las credenciales de Reddit.")
                return None

            return praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                check_for_async=False
            )
        except Exception as e:
            logger.error(f"Error al conectar con Reddit: {e}")
            return None

    def collect_posts(self, source_name: str, time_window_hours: int = 24) -> List[Post]:
        """
        Escanea un subreddit específico buscando posts recientes.
        
        Args:
            source_name: Nombre del subreddit a escanear.
            time_window_hours: Ventana de tiempo en horas para considerar posts.
            
        Returns:
            Una lista de entidades Post con los posts encontrados.
        """
        collected_posts: List[Post] = []
        if not self.reddit:
            logger.error("La instancia de Reddit no está disponible. No se puede escanear.")
            return collected_posts

        try:
            subreddit = self.reddit.subreddit(source_name)
            logger.info(f"🔍 Escaneando r/{source_name} (últimas {time_window_hours}h)...")
            
            # Analizar posts nuevos y calientes
            for post_source in [subreddit.new(limit=100), subreddit.hot(limit=50)]:
                for submission in post_source:
                    post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    if post_time < datetime.now(timezone.utc) - timedelta(hours=time_window_hours):
                        continue
                    
                    collected_posts.append(Post(
                        id=submission.id,
                        title=submission.title,
                        url=submission.url,
                        subreddit=source_name,
                        created_utc=post_time
                    ))
            
            logger.info(f"✅ r/{source_name}: {len(collected_posts)} posts recolectados.")
            return collected_posts
            
        except Exception as e:
            logger.error(f"💥 Error escaneando r/{source_name}: {e}")
            return []

    def extract_tickers_from_text(self, text: str) -> List[str]:
        """
        Extrae tickers de criptomonedas de un texto usando regex.
        """
        found_tickers = []
        text_upper = text.upper()
        
        # Buscar tickers conocidos
        for ticker in TARGET_TICKERS:
            patterns = [
                rf'\b{ticker}\b', rf'\${ticker}\b', rf'\b{ticker}/USD\b',
                rf'\b{ticker}/USDT\b', rf'\b{ticker}-USD\b'
            ]
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    found_tickers.append(ticker)
                    break
        
        # Buscar tickers potenciales con patrones generales
        general_patterns = [
            r'\$([A-Z]{2,6})\b',
            r'\b([A-Z]{2,6})/USD\b',
            r'\b([A-Z]{2,6})/USDT\b',
            r'\b([A-Z]{2,6})-USD\b',
            r'\b([A-Z]{3,6})\s+(?:COIN|TOKEN|PUMP|MOON|TO THE MOON)',
            r'\b([A-Z]{3,6})\s+(?:IS|WILL|GONNA)\s+(?:PUMP|MOON)',
        ]
        
        excluded = {'USD', 'USDT', 'THE', 'AND', 'FOR', 'YOU', 'ARE', 'CAN', 'NOT', 
                    'BUT', 'ALL', 'NEW', 'GET', 'NOW', 'OUT', 'WAY', 'WHO', 'OIL', 
                    'BOT', 'API', 'CEO', 'ATH', 'ATL', 'DCA', 'HOT', 'TOP', 'LOW', 
                    'BIG', 'BAD', 'GOD'}
        
        common_words = {'buy', 'sell', 'hold', 'pump', 'dump', 'moon', 'bear', 'bull', 'long', 'short'}

        for pattern in general_patterns:
            matches = re.findall(pattern, text_upper)
            for match in matches:
                if match not in excluded and match not in found_tickers and match.lower() not in common_words:
                    found_tickers.append(match)
        
        return list(set(found_tickers)) # Devolver tickers únicos 