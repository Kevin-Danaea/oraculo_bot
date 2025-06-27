#!/usr/bin/env python3
"""
Procesador de datos históricos de Reddit con análisis de sentimiento.
Procesa archivos .zst masivos de Reddit y los enriquece con análisis usando Gemini.
Guarda directamente en BigQuery para análisis masivo de datos históricos.

Uso:
    python procesador_historico.py path/to/reddit_data.zst

Características:
- Procesamiento en streaming (línea por línea) para eficiencia de memoria
- Inserción en lotes directa en BigQuery para análisis masivo
- Fallback a SQLite local en caso de problemas con BigQuery
- Manejo robusto de rate limits de API con exponential backoff
- Barra de progreso visual con tqdm
"""

import argparse
import concurrent.futures
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import psutil

from google import genai
import pandas as pd
import pandas_gbq
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# Importar configuración y modelos del proyecto
from shared.config.settings import settings
from shared.database.models import Base

# Configuración del script
BATCH_SIZE = 500  # Tamaño del lote para inserción en BD
PARALLEL_BATCH_SIZE = 1000  # Tamaño del lote para procesamiento paralelo de IA
MAX_WORKERS = 15  # Número máximo de hilos para procesamiento concurrente (ajustado para rate limit)
MAX_RETRIES = 5   # Máximo número de reintentos para API
INITIAL_RETRY_DELAY = 5  # Delay inicial en segundos para exponential backoff
DB_INSERT_RETRIES = 3  # Reintentos para inserción en base de datos
FALLBACK_DB_PATH = "fallback_oraculo.db"  # Ruta de la base de datos SQLite de fallback
CHECKPOINT_FILE = "procesamiento_checkpoint.txt"  # Archivo para guardar progreso
PROCESSED_URLS_FILE = "urls_procesadas.txt"  # Archivo para guardar URLs ya procesadas

# Listas de vocabulario controlado para validación
VALID_EMOTIONS = ['Euforia', 'Optimismo', 'Neutral', 'Incertidumbre', 'Miedo']
VALID_CATEGORIES = ['Regulación', 'Tecnología/Adopción', 'Mercado/Trading', 'Seguridad', 'Macroeconomía']

# Subreddits relevantes para crypto
CRYPTO_SUBREDDITS = {
    'CryptoCurrency', 'cryptocurrency', 'Bitcoin', 'bitcoin', 'ethereum', 'Ethereum',
    'ethtrader', 'defi', 'DeFi', 'CryptoMoonShots', 'cryptomoonshots', 'SatoshiStreetBets',
    'altcoin', 'CryptoCurrencyTrading', 'CryptoMarkets', 'Crypto_com', 'binance',
    'Coinbase', 'dogecoin', 'litecoin', 'ripple', 'cardano'
}

# Dominios de noticias confiables
TRUSTED_NEWS_DOMAINS = {
    'coindesk.com', 'cointelegraph.com', 'decrypt.co', 'bloomberg.com',
    'reuters.com', 'cnbc.com', 'forbes.com', 'wsj.com', 'ft.com',
    'coinbase.com', 'kraken.com', 'binance.com', 'crypto.com'
}

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('procesador_historico.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configurar el handler del stdout para UTF-8 en Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def process_text_batch_parallel(analyzer: 'SentimentAnalyzer', tasks_to_process: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Procesa un lote de tareas de análisis de sentimiento en paralelo.
    
    Args:
        analyzer: Instancia del analizador de sentimientos
        tasks_to_process: Lista de tareas preparadas para análisis
        
    Returns:
        Lista de resultados de análisis correspondientes a cada tarea
    """
    def analyze_single_task(task_data):
        """Función auxiliar para procesar una sola tarea."""
        try:
            return analyzer.analyze_text_with_gemini(task_data['text_to_analyze'])
        except Exception as e:
            logger.error(f"Error analizando tarea: {e}")
            return analyzer._get_default_analysis()
    
    # Procesar tareas en paralelo usando ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Enviar todas las tareas al pool de hilos
        future_to_task = {
            executor.submit(analyze_single_task, task): task 
            for task in tasks_to_process
        }
        
        results = []
        # Recoger resultados en el mismo orden que las tareas
        for task in tasks_to_process:
            # Buscar el future correspondiente a esta tarea
            for future, original_task in future_to_task.items():
                if original_task is task:
                    try:
                        analysis_result = future.result()
                        results.append(analysis_result)
                    except Exception as e:
                        logger.error(f"Error procesando future: {e}")
                        results.append(analyzer._get_default_analysis())
                    break
    
    return results

def check_bigquery_connection() -> bool:
    """
    Verifica que la conexión a BigQuery funcione correctamente.
    
    Returns:
        True si la conexión es exitosa, False en caso contrario
    """
    logger.info("[CHECK] Verificando conexión a BigQuery...")
    try:
        # Verificar variables de entorno necesarias
        project_id = settings.GOOGLE_CLOUD_PROJECT_ID
        if not project_id:
            logger.error("[ERROR] GOOGLE_CLOUD_PROJECT_ID no está configurada")
            return False
        
        # Ejecutar una consulta simple para verificar la conexión
        test_query = f"SELECT 1 as test_connection"
        df_test = pandas_gbq.read_gbq(test_query, project_id=project_id)
        
        if df_test is not None and len(df_test) > 0 and df_test.iat[0, 0] == 1:
            logger.info("[OK] Conexión a BigQuery verificada exitosamente")
            
            # Verificar que existe la tabla de destino
            table_check_query = f"""
            SELECT COUNT(*) as table_exists
            FROM `{project_id}.oraculo_data.INFORMATION_SCHEMA.TABLES`
            WHERE table_name = 'noticias_historicas'
            """
            
            df_table = pandas_gbq.read_gbq(table_check_query, project_id=project_id)
            if df_table is not None and len(df_table) > 0 and df_table.iat[0, 0] > 0:
                logger.info("[OK] Tabla 'noticias_historicas' encontrada en BigQuery")
                return True
            else:
                logger.error("[ERROR] Tabla 'noticias_historicas' no encontrada en BigQuery")
                return False
        else:
            logger.error("[ERROR] La consulta de prueba a BigQuery no devolvió el resultado esperado")
            return False
                
    except Exception as e:
        logger.error(f"[ERROR] Error al conectar con BigQuery: {e}")
        return False

def check_gemini_api() -> bool:
    """
    Verifica que la API de Gemini funcione correctamente con una llamada de prueba.
    
    Returns:
        True si la API funciona correctamente, False en caso contrario
    """
    logger.info("[CHECK] Verificando conexión a la API de Gemini...")
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # Texto de prueba simple
        test_text = "Bitcoin alcanza nuevo máximo histórico tras adopción institucional"
        test_prompt = f"""
        Analiza el siguiente texto sobre criptomonedas y devuelve ÚNICAMENTE un JSON válido con esta estructura:
        
        {{
            "sentiment_score": float entre -1.0 y 1.0,
            "primary_emotion": "una de estas opciones EXACTAS: {', '.join(VALID_EMOTIONS)}",
            "news_category": "una de estas opciones EXACTAS: {', '.join(VALID_CATEGORIES)}"
        }}
        
        Texto: "{test_text}"
        
        Responde ÚNICAMENTE con el JSON:
        """
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=test_prompt
        )
        
        if not response.text or response.text.strip() == "":
            logger.error("[ERROR] La API de Gemini devolvió una respuesta vacía")
            return False
        
        # Intentar parsear la respuesta como JSON
        try:
            clean_text = response.text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text.replace('```json\n', '').replace('\n```', '')
            elif clean_text.startswith('```'):
                lines = clean_text.split('\n')
                clean_text = '\n'.join(lines[1:-1])
            
            result = json.loads(clean_text)
            
            # Validar que tiene las claves esperadas
            required_keys = ['sentiment_score', 'primary_emotion', 'news_category']
            for key in required_keys:
                if key not in result:
                    logger.error(f"[ERROR] La respuesta de Gemini no contiene la clave '{key}'")
                    return False
            
            # Validar tipos y valores
            sentiment_score = result.get('sentiment_score')
            if not isinstance(sentiment_score, (int, float)) or not (-1.0 <= sentiment_score <= 1.0):
                logger.error(f"[ERROR] sentiment_score inválido: {sentiment_score}")
                return False
            
            primary_emotion = result.get('primary_emotion')
            if primary_emotion not in VALID_EMOTIONS:
                logger.error(f"[ERROR] primary_emotion inválida: {primary_emotion}")
                return False
            
            news_category = result.get('news_category')
            if news_category not in VALID_CATEGORIES:
                logger.error(f"[ERROR] news_category inválida: {news_category}")
                return False
            
            logger.info("[OK] API de Gemini verificada exitosamente")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Error parseando JSON de respuesta de Gemini: {e}")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Error al probar la API de Gemini: {e}")
        return False

def check_zstd_availability() -> bool:
    """
    Verifica que el comando zstd esté disponible en el sistema.
    Proporciona instrucciones de instalación si no está disponible.
    
    Returns:
        True si zstd está disponible, False en caso contrario
    """
    logger.info("[CHECK] Verificando disponibilidad del comando zstd...")
    try:
        result = subprocess.run(['zstd', '--version'], capture_output=True, check=True, text=True)
        version_info = result.stdout.strip().split('\n')[0] if result.stdout else "versión desconocida"
        logger.info(f"[OK] Comando zstd encontrado: {version_info}")
        return True
    except FileNotFoundError:
        logger.error("[ERROR] Comando 'zstd' no encontrado en el sistema")
        logger.error("")
        logger.error("💡 INSTRUCCIONES DE INSTALACIÓN:")
        logger.error("   📦 Windows (con winget):")
        logger.error("       winget install facebook.zstd")
        logger.error("")
        logger.error("   📦 Windows (manual):")
        logger.error("       1. Descarga desde: https://github.com/facebook/zstd/releases")
        logger.error("       2. Extrae zstd.exe a una carpeta en tu PATH")
        logger.error("")
        logger.error("   📦 macOS:")
        logger.error("       brew install zstd")
        logger.error("")
        logger.error("   📦 Ubuntu/Debian:")
        logger.error("       sudo apt install zstd")
        logger.error("")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Error ejecutando comando zstd: {e}")
        return False

class SentimentAnalyzer:
    """Analizador de sentimientos usando Google Gemini."""
    
    def __init__(self):
        """Inicializa el cliente de Gemini."""
        try:
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            logger.info("Cliente de Gemini inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al configurar el cliente de Gemini: {e}")
            self.client = None
    
    def analyze_text_with_gemini(self, text: str) -> Dict[str, Any]:
        """
        Analiza el texto usando Gemini con manejo de rate limits.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Dict con sentiment_score, primary_emotion y news_category
        """
        if not self.client:
            logger.warning("Cliente de Gemini no disponible, usando valores por defecto")
            return self._get_default_analysis()
        
        prompt = self._build_prompt(text)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt
                )
                
                # Pausa para cumplir rate limit de 2000 RPM
                time.sleep(0.5)
                
                if not response.text or response.text.strip() == "":
                    logger.warning(f"Respuesta vacía para: '{text[:50]}...'")
                    return self._get_default_analysis()
                
                return self._parse_response(response.text)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Manejo específico de rate limits
                if "resource_exhausted" in error_msg or "429" in error_msg:
                    delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limit alcanzado. Esperando {delay}s (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Error no recuperable analizando texto: {e}")
                    return self._get_default_analysis()
        
        logger.error(f"Se agotaron los reintentos para: '{text[:50]}...'")
        return self._get_default_analysis()
    
    def _build_prompt(self, text: str) -> str:
        """Construye el prompt para Gemini."""
        return f"""
        Actúa como un analista cuantitativo de sentimiento, especializado en el mercado de criptomonedas. Tu tarea es evaluar el siguiente texto y devolver un análisis estructurado.

        Analiza el siguiente texto sobre criptomomedas y devuelve ÚNICAMENTE un JSON válido con esta estructura:
        
        {{
            "sentiment_score": float entre -1.0 y 1.0,
            "primary_emotion": "una de estas opciones EXACTAS: {', '.join(VALID_EMOTIONS)}",
            "news_category": "una de estas opciones EXACTAS: {', '.join(VALID_CATEGORIES)}"
        }}
        
        CRITERIOS PARA SENTIMENT_SCORE:
        - Muy positivo (adopción masiva, ATH, buenas regulaciones): 0.6 a 1.0
        - Positivo (desarrollos, adopción gradual): 0.1 a 0.5
        - Neutral (informativo, sin impacto claro): -0.1 a 0.1
        - Negativo (regulaciones adversas, caídas): -0.5 a -0.1
        - Muy negativo (hacks, prohibiciones, crisis): -1.0 a -0.6
        
        CRITERIOS PARA PRIMARY_EMOTION:
        - Euforia: ATH, adopción masiva, noticias revolucionarias
        - Optimismo: Desarrollos positivos, buenas noticias graduales
        - Neutral: Noticias informativas sin carga emocional
        - Incertidumbre: Rumores, decisiones pendientes, noticias ambiguas
        - Miedo: Regulaciones adversas, hacks, crisis, caídas abruptas
        
        CRITERIOS PARA NEWS_CATEGORY:
        - Regulación: Leyes, normativas, decisiones gubernamentales
        - Tecnología/Adopción: Avances técnicos, nuevas integraciones
        - Mercado/Trading: Precios, análisis técnico, movimientos de mercado
        - Seguridad: Hacks, vulnerabilidades, protocolos de seguridad
        - Macroeconomía: Inflación, política monetaria, economía global
        
        Texto: "{text}"
        
        Responde ÚNICAMENTE con el JSON:
        """
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea y valida la respuesta de Gemini."""
        try:
            # Limpiar respuesta de bloques de código markdown
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text.replace('```json\n', '').replace('\n```', '')
            elif clean_text.startswith('```'):
                lines = clean_text.split('\n')
                clean_text = '\n'.join(lines[1:-1])
            
            result = json.loads(clean_text)
            
            # Validar y normalizar los datos
            sentiment_score = float(result.get("sentiment_score", 0.0))
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            
            primary_emotion = result.get("primary_emotion", "Neutral")
            if primary_emotion not in VALID_EMOTIONS:
                logger.warning(f"Emoción inválida '{primary_emotion}', usando 'Neutral'")
                primary_emotion = "Neutral"
            
            news_category = result.get("news_category", "Mercado/Trading")
            if news_category not in VALID_CATEGORIES:
                logger.warning(f"Categoría inválida '{news_category}', usando 'Mercado/Trading'")
                news_category = "Mercado/Trading"
            
            return {
                "sentiment_score": sentiment_score,
                "primary_emotion": primary_emotion,
                "news_category": news_category
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Gemini: {e}. Respuesta: '{response_text[:200]}...'")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Retorna análisis por defecto cuando falla el procesamiento."""
        return {
            "sentiment_score": 0.0,
            "primary_emotion": "Neutral",
            "news_category": "Mercado/Trading"
        }


class RedditPostProcessor:
    """Procesador de posts de Reddit con filtros de calidad."""
    
    def __init__(self, analyzer: SentimentAnalyzer):
        """Inicializa el procesador con el analizador de sentimientos."""
        self.analyzer = analyzer
        self.processed_urls = load_processed_urls()  # Cargar URLs ya procesadas
        logger.info(f"🔄 Iniciando con {len(self.processed_urls):,} URLs ya procesadas en memoria")
        self.stats = {
            'total_read': 0,
            'filtered_irrelevant_subreddit': 0,
            'filtered_low_quality': 0,
            'filtered_low_engagement': 0,
            'filtered_short_text': 0,
            'filtered_bad_link': 0,
            'filtered_duplicate_url': 0,  # Nueva métrica para duplicados
            'queued_for_processing': 0,  # Tareas encoladas para análisis IA
            'processed': 0,
            'errors': 0
        }
    
    def process_post(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Procesa una línea del archivo de Reddit aplicando filtros.
        
        Args:
            line: Línea JSON del archivo de Reddit
            
        Returns:
            Dict con datos del post procesado o None si se filtra
        """
        self.stats['total_read'] += 1
        
        try:
            post = json.loads(line.strip())
        except json.JSONDecodeError:
            self.stats['errors'] += 1
            return None
        
        # Aplicar pipeline de filtros
        if not self._filter_subreddit_relevance(post):
            self.stats['filtered_irrelevant_subreddit'] += 1
            return None
        
        if not self._filter_basic_quality(post):
            self.stats['filtered_low_quality'] += 1
            return None
        
        if not self._filter_minimum_engagement(post):
            self.stats['filtered_low_engagement'] += 1
            return None
        
        # Determinar tipo de post y texto a analizar
        text_to_analyze = self._extract_text_to_analyze(post)
        if not text_to_analyze:
            if post.get('is_self', False):
                self.stats['filtered_short_text'] += 1
            else:
                self.stats['filtered_bad_link'] += 1
            return None
        
        # Verificar si ya procesamos esta URL
        post_url = post.get('url', f"https://reddit.com{post.get('permalink', '')}")
        if post_url in self.processed_urls:
            self.stats['filtered_duplicate_url'] += 1
            return None
        
        # Analizar sentimiento
        try:
            analysis = self.analyzer.analyze_text_with_gemini(text_to_analyze)
            
            # Agregar URL al set de procesadas DESPUÉS de análisis exitoso
            self.processed_urls.add(post_url)
            
            # Preparar datos para inserción en BD
            post_data = {
                'source': 'reddit_historical',
                'headline': text_to_analyze,
                'url': post_url,
                'published_at': format_utc_timestamp(post.get('created_utc', 0)),  # Formato UTC ISO 8601
                'sentiment_score': analysis['sentiment_score'],
                'primary_emotion': analysis['primary_emotion'],
                'news_category': analysis['news_category']
            }
            
            self.stats['processed'] += 1
            return post_data
            
        except Exception as e:
            logger.error(f"Error procesando post: {e}")
            self.stats['errors'] += 1
            return None
    
    def _filter_subreddit_relevance(self, post: Dict) -> bool:
        """Filtra por relevancia del subreddit."""
        subreddit = post.get('subreddit', '').strip()
        return subreddit in CRYPTO_SUBREDDITS
    
    def _filter_basic_quality(self, post: Dict) -> bool:
        """Filtra por calidad básica del post."""
        selftext = post.get('selftext', '').strip()
        if selftext in ['[deleted]', '[removed]']:
            return False
        
        if post.get('stickied', False):
            return False
        
        return True
    
    def _filter_minimum_engagement(self, post: Dict) -> bool:
        """Filtra por engagement mínimo."""
        score = post.get('score', 0)
        return score >= 10
    
    def _extract_text_to_analyze(self, post: Dict) -> Optional[str]:
        """Extrae el texto a analizar según el tipo de post."""
        title = post.get('title', '').strip()
        is_self = post.get('is_self', False)
        
        if is_self:
            # Post de texto
            selftext = post.get('selftext', '').strip()
            if len(selftext) > 150:
                return f"{title} {selftext}"
            return None
        else:
            # Post de enlace
            url = post.get('url', '')
            if self._is_trusted_domain(url):
                return title
            return None
    
    def _is_trusted_domain(self, url: str) -> bool:
        """Verifica si el dominio está en la lista blanca."""
        try:
            domain = urlparse(url).netloc.lower()
            # Remover 'www.' si existe
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain in TRUSTED_NEWS_DOMAINS
        except Exception:
            return False
    
    def prepare_task_if_valid(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Aplica filtros a una línea del archivo y prepara la tarea para análisis de IA.
        
        Args:
            line: Línea JSON del archivo de Reddit
            
        Returns:
            Dict con datos de la tarea preparada o None si se filtra
        """
        self.stats['total_read'] += 1
        
        try:
            post = json.loads(line.strip())
        except json.JSONDecodeError:
            self.stats['errors'] += 1
            return None
        
        # Aplicar pipeline de filtros
        if not self._filter_subreddit_relevance(post):
            self.stats['filtered_irrelevant_subreddit'] += 1
            return None
        
        if not self._filter_basic_quality(post):
            self.stats['filtered_low_quality'] += 1
            return None
        
        if not self._filter_minimum_engagement(post):
            self.stats['filtered_low_engagement'] += 1
            return None
        
        # Determinar tipo de post y texto a analizar
        text_to_analyze = self._extract_text_to_analyze(post)
        if not text_to_analyze:
            if post.get('is_self', False):
                self.stats['filtered_short_text'] += 1
            else:
                self.stats['filtered_bad_link'] += 1
            return None
        
        # Verificar si ya procesamos esta URL
        post_url = post.get('url', f"https://reddit.com{post.get('permalink', '')}")
        if post_url in self.processed_urls:
            self.stats['filtered_duplicate_url'] += 1
            return None
        
        # Incrementar contador de tareas encoladas
        self.stats['queued_for_processing'] += 1
        
        # Devolver tarea preparada para análisis de IA
        return {
            'text_to_analyze': text_to_analyze,
            'post_url': post_url,
            'created_utc': post.get('created_utc', 0)
        }
    
    def create_post_data_from_analysis(self, task_data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea los datos del post a partir de una tarea y su análisis de IA.
        
        Args:
            task_data: Datos de la tarea preparada
            analysis: Resultado del análisis de sentimiento
            
        Returns:
            Dict con datos del post procesado
        """
        # Agregar URL al set de procesadas
        self.processed_urls.add(task_data['post_url'])
        
        # Preparar datos para inserción en BD
        post_data = {
            'source': 'reddit_historical',
            'headline': task_data['text_to_analyze'],
            'url': task_data['post_url'],
            'published_at': format_utc_timestamp(task_data['created_utc']),
            'sentiment_score': analysis['sentiment_score'],
            'primary_emotion': analysis['primary_emotion'],
            'news_category': analysis['news_category']
        }
        
        self.stats['processed'] += 1
        return post_data

    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas del procesamiento."""
        return self.stats.copy()


class DatabaseManager:
    """Manejador de la base de datos con inserción en lotes y fallback a SQLite."""
    
    def __init__(self):
        """Inicializa la conexión a BigQuery y fallback SQLite."""
        try:
            # Configurar BigQuery
            self.project_id = settings.GOOGLE_CLOUD_PROJECT_ID
            if not self.project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT_ID no configurada")
            
            self.table_id = f"{self.project_id}.oraculo_data.noticias_historicas"
            logger.info(f"[DATABASE] Configurado para BigQuery: {self.table_id}")
            
            # Inicializar base de datos SQLite de fallback
            self._init_fallback_db()
            
        except Exception as e:
            logger.error(f"Error configurando DatabaseManager: {e}")
            raise
    
    def _init_fallback_db(self):
        """Inicializa la base de datos SQLite de fallback."""
        try:
            self.fallback_engine = create_engine(f"sqlite:///{FALLBACK_DB_PATH}")
            Base.metadata.create_all(bind=self.fallback_engine)
            FallbackSession = sessionmaker(bind=self.fallback_engine)
            self.fallback_session = FallbackSession()
        except Exception as e:
            logger.error(f"Error inicializando base de datos de fallback: {e}")
            self.fallback_session = None
    
    def _insert_to_fallback(self, batch_data: List[Dict[str, Any]]) -> bool:
        """
        Inserta datos en la base de datos SQLite de fallback.
        
        Args:
            batch_data: Lista de diccionarios con datos de posts
            
        Returns:
            True si la inserción fue exitosa
        """
        if not self.fallback_session:
            logger.error("Sesión de fallback no disponible")
            return False
            
        try:
            # Usar raw SQL con INSERT OR IGNORE para SQLite
            from sqlalchemy import text
            
            insert_sql = """
            INSERT INTO noticias (source, headline, url, published_at, sentiment_score, primary_emotion, news_category)
            VALUES (:source, :headline, :url, :published_at, :sentiment_score, :primary_emotion, :news_category)
            ON CONFLICT(url) DO UPDATE SET
                headline = CASE 
                    WHEN LENGTH(excluded.headline) > LENGTH(noticias.headline) THEN excluded.headline
                    ELSE noticias.headline
                END,
                sentiment_score = excluded.sentiment_score,
                primary_emotion = excluded.primary_emotion,
                news_category = excluded.news_category
            """
            
            self.fallback_session.execute(text(insert_sql), batch_data)
            self.fallback_session.commit()
            logger.warning(f"[FALLBACK] Lote de {len(batch_data)} registros guardado en SQLite local (duplicados actualizados si son mejores)")
            return True
        except Exception as e:
            logger.error(f"Error insertando en base de datos de fallback: {e}")
            self.fallback_session.rollback()
            return False
    
    def insert_batch(self, batch_data: List[Dict[str, Any]]) -> bool:
        """
        Inserta un lote de datos en BigQuery con reintentos y fallback.
        
        Args:
            batch_data: Lista de diccionarios con datos de posts
            
        Returns:
            True si la inserción fue exitosa (en BigQuery o fallback)
        """
        # Intentar inserción en BigQuery
        for attempt in range(DB_INSERT_RETRIES):
            try:
                # Convertir a DataFrame para pandas_gbq
                df = pd.DataFrame(batch_data)
                
                # Renombrar columnas para que coincidan con BigQuery si es necesario
                # BigQuery es sensible a mayúsculas/minúsculas
                df = df.rename(columns={
                    'source': 'source',
                    'headline': 'headline', 
                    'url': 'url',
                    'published_at': 'published_at',
                    'sentiment_score': 'sentiment_score',
                    'primary_emotion': 'primary_emotion',
                    'news_category': 'news_category'
                })
                
                # Insertar en BigQuery con manejo de duplicados
                pandas_gbq.to_gbq(
                    df,
                    destination_table='oraculo_data.noticias_historicas',
                    project_id=self.project_id,
                    if_exists='append',  # Agregar nuevos registros
                    progress_bar=False,
                    chunksize=len(batch_data)  # Insertar todo el lote de una vez
                )
                
                logger.info(f"Lote de {len(batch_data)} registros insertado exitosamente en BigQuery")
                return True
                
            except Exception as e:
                logger.warning(f"Error en intento {attempt + 1}/{DB_INSERT_RETRIES} de inserción en BigQuery: {e}")
                
                # Si no es el último intento, esperar antes de reintentar
                if attempt < DB_INSERT_RETRIES - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Esperando {wait_time}s antes de reintentar...")
                    time.sleep(wait_time)
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"[ERROR] Falló la inserción en BigQuery después de {DB_INSERT_RETRIES} intentos")
        
        # Intentar fallback a SQLite
        logger.warning("[RETRY] Intentando guardar en base de datos de fallback...")
        if self._insert_to_fallback(batch_data):
            return True
        else:
            logger.error("[ERROR] También falló la inserción en base de datos de fallback")
            return False
    
    def close(self):
        """Cierra las conexiones a las bases de datos."""
        if hasattr(self, 'fallback_session') and self.fallback_session:
            self.fallback_session.close()


def get_file_size(filepath: str) -> int:
    """Obtiene el tamaño del archivo en bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def process_reddit_file(filepath: str) -> Dict[str, Any]:
    """
    Procesa el archivo de Reddit histórico completo.
    
    Args:
        filepath: Ruta al archivo .zst
        
    Returns:
        Dict con estadísticas del procesamiento
    """
    logger.info(f"Iniciando procesamiento de archivo: {filepath}")
    
    # Obtener información básica del archivo
    file_size_bytes = get_file_size(filepath)
    file_size_gb = file_size_bytes / (1024**3)
    
    logger.info(f"📊 ANÁLISIS DEL ARCHIVO:")
    logger.info(f"   Tamaño: {file_size_gb:.2f} GB")
    logger.info(f"   Estrategia: Comando externo zstd con streaming")
    logger.info(f"   Procesamiento: Línea por línea sin pre-carga")
    logger.info(f"   Parámetros: --long=31 (window hasta 2GB), --memory=2048MB")
    
    # Variables para procesamiento en lotes
    batch_data = []
    batch_insertions = 0
    start_time = time.time()
    db_manager = None
    
    # Cargar checkpoint si existe
    start_line = load_checkpoint()
    if start_line > 0:
        logger.info(f"🔄 REANUDANDO procesamiento desde línea {start_line:,}")
    else:
        logger.info("🚀 INICIANDO procesamiento desde el principio")
    
    try:
        # Inicializar componentes
        logger.info("Inicializando componentes del procesador...")
        analyzer = SentimentAnalyzer()
        processor = RedditPostProcessor(analyzer)
        db_manager = DatabaseManager()
        
        # Verificar que zstd esté disponible
        if not check_zstd_availability():
            logger.error("❌ ERROR: Comando 'zstd' no disponible. Terminando script.")
            sys.exit(1)
        
        logger.info("Iniciando procesamiento con descompresión streaming...")
        # Usamos subprocess para descomprimir streaming con zstd command line
        # --long=31: Permite window sizes hasta 2GB (2^31 bytes)
        # --memory=3072MB: Límite de memoria para decodificación
        process = subprocess.Popen(
            ['zstd', '-d', '-c', '--long=31', '--memory=2048MB', filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1  # Line buffered
        )
        
        # Procesar con barra de progreso y lógica de lotes paralelos
        with tqdm(desc="Procesando posts", unit="posts", total=None) as pbar:
            line_count = 0
            tasks_to_process = []  # Acumulador de tareas para procesamiento paralelo
            
            try:
                # Verificar que el proceso esté funcionando
                if process.stdout is None:
                    raise RuntimeError("No se pudo abrir stdout del proceso zstd")
                
                # Ahora podemos iterar línea por línea desde el proceso zstd
                for line in process.stdout:
                    line_count += 1
                    
                    # Saltar líneas ya procesadas (checkpoint)
                    if line_count <= start_line:
                        pbar.update(1)
                        continue
                    
                    try:
                        if not line.strip():
                            pbar.update(1)
                            continue
                        
                        # Aplicar filtros y preparar tarea si es válida
                        task_data = processor.prepare_task_if_valid(line)
                        
                        if task_data:
                            tasks_to_process.append(task_data)
                        
                        # Cuando se acumule un lote suficiente, procesar en paralelo
                        if len(tasks_to_process) >= PARALLEL_BATCH_SIZE:
                            logger.info(f"Procesando lote de {len(tasks_to_process)} tareas en paralelo...")
                            
                            # Procesar tareas en paralelo
                            analysis_results = process_text_batch_parallel(analyzer, tasks_to_process)
                            
                            # Crear post_data a partir de los resultados
                            for task_data, analysis in zip(tasks_to_process, analysis_results):
                                try:
                                    post_data = processor.create_post_data_from_analysis(task_data, analysis)
                                    batch_data.append(post_data)
                                except Exception as e:
                                    logger.error(f"Error creando post_data: {e}")
                                    processor.stats['errors'] += 1
                            
                            # Limpiar lista de tareas
                            tasks_to_process.clear()
                            
                            # Insertar en BD cuando se alcance el tamaño objetivo
                            while len(batch_data) >= BATCH_SIZE:
                                current_batch = batch_data[:BATCH_SIZE]
                                batch_data = batch_data[BATCH_SIZE:]
                                
                                success = db_manager.insert_batch(current_batch)
                                if success:
                                    batch_insertions += 1
                                else:
                                    logger.error("Falló inserción de lote en BigQuery y fallback")
                            
                            # Guardar progreso periódicamente
                            save_checkpoint(line_count)
                            if batch_insertions % 10 == 0:
                                save_processed_urls(processor.processed_urls)
                        
                        pbar.update(1)
                        
                        # Actualizar descripción de progreso cada 1000 posts
                        if pbar.n % 1000 == 0:
                            stats = processor.get_stats()
                            # Monitoreo de memoria cada 10,000 posts
                            if pbar.n % 10000 == 0:
                                memory_percent = psutil.virtual_memory().percent
                                logger.info(f"Checkpoint {pbar.n:,}: Uso de memoria: {memory_percent:.1f}%")
                            
                            pbar.set_description(
                                f"Procesando posts (encolados: {stats['queued_for_processing']}, "
                                f"completados: {stats['processed']}, errores: {stats['errors']})"
                            )
                    
                    except json.JSONDecodeError:
                        # Ignoramos líneas que no son JSON válido, es común en estos archivos
                        pbar.update(1)
                        continue
                    except Exception as e:
                        logger.error(f"Error procesando línea {line_count}: {e}")
                        pbar.update(1)
                        continue
                
                # Procesar tareas restantes al final del archivo
                if tasks_to_process:
                    logger.info(f"Procesando lote final de {len(tasks_to_process)} tareas en paralelo...")
                    
                    # Procesar tareas finales en paralelo
                    analysis_results = process_text_batch_parallel(analyzer, tasks_to_process)
                    
                    # Crear post_data a partir de los resultados
                    for task_data, analysis in zip(tasks_to_process, analysis_results):
                        try:
                            post_data = processor.create_post_data_from_analysis(task_data, analysis)
                            batch_data.append(post_data)
                        except Exception as e:
                            logger.error(f"Error creando post_data: {e}")
                            processor.stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error en el procesamiento con comando zstd: {e}")
                raise
            finally:
                # Asegurar que el proceso se termine correctamente
                if process.stdout:
                    process.stdout.close()
                return_code = process.wait()
                if return_code != 0:
                    stderr_output = ""
                    if process.stderr:
                        stderr_output = process.stderr.read()
                    logger.error(f"Error en comando zstd (código {return_code}): {stderr_output}")
                    raise subprocess.CalledProcessError(return_code, 'zstd', stderr_output)
        
        # Insertar lote final si tiene datos
        if batch_data:
            success = db_manager.insert_batch(batch_data)
            if success:
                batch_insertions += 1
            else:
                logger.error("Falló inserción del lote final en BigQuery y fallback")
        
        # Guardar URLs procesadas antes de limpiar
        save_processed_urls(processor.processed_urls)
    
    except Exception as e:
        logger.error(f"Error en el procesamiento: {e}")
        if db_manager:
            db_manager.close()
        raise
    
    finally:
        if db_manager:
            db_manager.close()
    
    # Calcular estadísticas finales
    end_time = time.time()
    processing_time = end_time - start_time
    stats = processor.get_stats()
    
    # Limpiar checkpoint al completar exitosamente
    clear_checkpoint()
    clear_processed_urls()
    
    logger.info("=" * 60)
    logger.info("PROCESAMIENTO COMPLETADO")
    logger.info("=" * 60)
    logger.info(f"Tiempo total: {processing_time:.2f} segundos")
    logger.info(f"Posts leídos: {stats['total_read']:,}")
    logger.info(f"Posts encolados para IA: {stats['queued_for_processing']:,}")
    logger.info(f"Posts completados: {stats['processed']:,}")
    logger.info(f"Lotes insertados: {batch_insertions}")
    logger.info(f"Errores: {stats['errors']:,}")
    logger.info("")
    
    # Verificar si se usó fallback
    if os.path.exists(FALLBACK_DB_PATH):
        file_size = os.path.getsize(FALLBACK_DB_PATH)
        if file_size > 0:
            logger.warning("[WARNING] ATENCIÓN: Se utilizó base de datos de fallback SQLite")
            logger.warning(f"   Archivo: {FALLBACK_DB_PATH}")
            logger.warning(f"   Tamaño: {file_size / (1024*1024):.2f} MB")
            logger.warning("   Recuerda migrar estos datos a BigQuery cuando sea posible")
        else:
            logger.info("[OK] No se requirió usar la base de datos de fallback")
    else:
        logger.info("[OK] No se requirió usar la base de datos de fallback")
    
    logger.info("")
    logger.info("FILTROS APLICADOS:")
    logger.info(f"  - Subreddit irrelevante: {stats['filtered_irrelevant_subreddit']:,}")
    logger.info(f"  - Baja calidad: {stats['filtered_low_quality']:,}")
    logger.info(f"  - Poco engagement: {stats['filtered_low_engagement']:,}")
    logger.info(f"  - Texto muy corto: {stats['filtered_short_text']:,}")
    logger.info(f"  - Enlace no confiable: {stats['filtered_bad_link']:,}")
    logger.info(f"  - URL duplicada: {stats['filtered_duplicate_url']:,}")
    logger.info("=" * 60)
    
    return {
        'success': True,
        'processing_time': processing_time,
        'posts_processed': stats['processed'],
        'batch_insertions': batch_insertions,
        'stats': stats
    }


def save_checkpoint(line_number: int) -> None:
    """Guarda el progreso actual en un archivo de checkpoint."""
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(str(line_number))
    except Exception as e:
        logger.warning(f"No se pudo guardar checkpoint: {e}")

def load_checkpoint() -> int:
    """Carga el progreso desde el archivo de checkpoint."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                line_number = int(f.read().strip())
            return line_number
        return 0
    except Exception as e:
        logger.warning(f"No se pudo cargar checkpoint: {e}")
        return 0

def clear_checkpoint() -> None:
    """Elimina el archivo de checkpoint al completar el procesamiento."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception as e:
        logger.warning(f"No se pudo eliminar checkpoint: {e}")


def save_processed_urls(processed_urls: set) -> None:
    """Guarda el set de URLs procesadas en un archivo."""
    try:
        with open(PROCESSED_URLS_FILE, 'w', encoding='utf-8') as f:
            for url in processed_urls:
                f.write(f"{url}\n")
    except Exception as e:
        logger.warning(f"No se pudieron guardar URLs procesadas: {e}")

def load_processed_urls() -> set:
    """Carga el set de URLs procesadas desde un archivo."""
    processed_urls = set()
    try:
        if os.path.exists(PROCESSED_URLS_FILE):
            with open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as f:
                processed_urls = {line.strip() for line in f if line.strip()}
        return processed_urls
    except Exception as e:
        logger.warning(f"No se pudieron cargar URLs procesadas: {e}")
        return set()

def clear_processed_urls() -> None:
    """Elimina el archivo de URLs procesadas al completar el procesamiento."""
    try:
        if os.path.exists(PROCESSED_URLS_FILE):
            os.remove(PROCESSED_URLS_FILE)
    except Exception as e:
        logger.warning(f"No se pudo eliminar archivo de URLs procesadas: {e}")


def format_utc_timestamp(timestamp: float) -> str:
    """
    Convierte un timestamp UTC a formato ISO 8601 con timezone UTC.
    
    Args:
        timestamp: Timestamp Unix en segundos (UTC)
        
    Returns:
        Fecha en formato ISO 8601: 2020-05-01T15:30:45+00:00
        
    Example:
        >>> format_utc_timestamp(1588346445.0)
        '2020-05-01T15:07:25+00:00'
    """
    if not timestamp or timestamp <= 0:
        # Si el timestamp es inválido, usar epoch como fallback
        timestamp = 0
    
    # Crear datetime en UTC
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    # Retornar en formato ISO 8601 con timezone UTC
    return dt_utc.isoformat()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description='Procesa archivos masivos de Reddit históricos con análisis de sentimiento'
    )
    parser.add_argument(
        'file_path',
        help='Ruta al archivo .zst de Reddit a procesar'
    )
    
    args = parser.parse_args()
    
    # Validar que el archivo existe
    if not os.path.exists(args.file_path):
        logger.error(f"El archivo no existe: {args.file_path}")
        sys.exit(1)
    
    # Validar extensión del archivo
    if not args.file_path.endswith('.zst'):
        logger.error("El archivo debe tener extensión .zst")
        sys.exit(1)
    
    # Validar configuración
    if not settings.GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY no configurada en el archivo .env")
        sys.exit(1)
    
    if not settings.GOOGLE_CLOUD_PROJECT_ID:
        logger.error("GOOGLE_CLOUD_PROJECT_ID no configurada en el archivo .env")
        sys.exit(1)
    
    # CHEQUEOS PREVIOS AL INICIO (Pre-flight Checks)
    logger.info("=" * 60)
    logger.info("REALIZANDO CHEQUEOS PREVIOS")
    logger.info("=" * 60)
    
    # Chequeo 1: Verificar conexión a BigQuery
    if not check_bigquery_connection():
        logger.error("[ERROR] Fallo en chequeo de BigQuery. Terminando script.")
        sys.exit(1)
    
    # Chequeo 2: Verificar API de Gemini
    if not check_gemini_api():
        logger.error("[ERROR] Fallo en chequeo de API de Gemini. Terminando script.")
        sys.exit(1)
    
    # Chequeo 3: Verificar disponibilidad de comando zstd
    if not check_zstd_availability():
        logger.error("[ERROR] Fallo en chequeo de comando zstd. Terminando script.")
        sys.exit(1)
    
    logger.info("[OK] Todos los chequeos previos completados exitosamente")
    logger.info("=" * 60)
    
    try:
        result = process_reddit_file(args.file_path)
        if result['success']:
            logger.info("[OK] Procesamiento completado exitosamente")
            sys.exit(0)
        else:
            logger.error("[ERROR] El procesamiento falló")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal en el procesamiento: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback completo:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()