"""
Hype Radar Service - Detector de Tendencias de Memecoins
========================================================

Servicio especializado en monitorear subreddits de alto riesgo y detectar
menciones frecuentes de memecoins/altcoins que podrían indicar pumps inminentes.
"""

import praw
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from shared.config.settings import settings
from shared.services.logging_config import get_logger
from shared.database import models
from shared.database.session import SessionLocal

logger = get_logger(__name__)

# Subreddits de alto riesgo para detectar hype (verificados y activos)
HYPE_SUBREDDITS = [
    'SatoshiStreetBets',        # Activo - pump discussions
    'CryptoMoonShots',          # Activo - new coin launches
    'CryptoCurrency',           # Activo - general crypto discussions
    'altcoin',                  # Activo - altcoin discussions
    'CryptoBets',               # Activo - high risk plays
    'SmallCryptos',             # Activo - small cap discussions
    'ethtrader',                # Activo - ethereum trading
    'defi'                      # Activo - DeFi discussions
]

# Lista de tickers de memecoins y altcoins populares para monitorear
TARGET_TICKERS = [
    # Memecoins principales
    'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'BOME',
    
    # Altcoins populares
    'ADA', 'DOT', 'LINK', 'UNI', 'AVAX', 'MATIC', 'ATOM',
    'LTC', 'BCH', 'XRP', 'TRX', 'VET', 'ALGO', 'HBAR',
    
    # DeFi tokens
    'AAVE', 'COMP', 'MKR', 'SNX', 'YFI', 'SUSHI', '1INCH',
    
    # Nuevos/trending
    'SOL', 'APT', 'SUI', 'ARB', 'OP', 'BLUR', 'ID'
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

def extract_tickers_from_text(text: str) -> List[str]:
    """
    Extrae tickers de criptomonedas de un texto usando regex.
    Detecta tanto tickers conocidos como nuevos tickers que cumplan el patrón.
    
    Args:
        text: Texto a analizar (título del post)
        
    Returns:
        List[str]: Lista de tickers encontrados
    """
    found_tickers = []
    text_upper = text.upper()
    
    # PASO 1: Buscar tickers conocidos de nuestra lista
    for ticker in TARGET_TICKERS:
        patterns = [
            rf'\b{ticker}\b',           # Ticker solo
            rf'\${ticker}\b',           # $TICKER
            rf'\b{ticker}/USD\b',       # TICKER/USD
            rf'\b{ticker}/USDT\b',      # TICKER/USDT
            rf'\b{ticker}-USD\b',       # TICKER-USD
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_upper):
                found_tickers.append(ticker)
                break  # Solo contar una vez por ticker
    
    # PASO 2: Buscar cualquier ticker potencial usando patrones generales
    # Detectar patrones como $XXX, XXX/USD, etc. donde XXX es 2-6 letras
    general_patterns = [
        r'\$([A-Z]{2,6})\b',                    # $TICKER
        r'\b([A-Z]{2,6})/USD\b',                # TICKER/USD
        r'\b([A-Z]{2,6})/USDT\b',               # TICKER/USDT  
        r'\b([A-Z]{2,6})-USD\b',                # TICKER-USD
        r'\b([A-Z]{3,6})\s+(?:COIN|TOKEN|PUMP|MOON|TO THE MOON)',  # TICKER seguido de palabras clave
        r'\b([A-Z]{3,6})\s+(?:IS|WILL|GONNA)\s+(?:PUMP|MOON)',     # "TICKER is pumping"
    ]
    
    for pattern in general_patterns:
        matches = re.findall(pattern, text_upper)
        for match in matches:
            # Filtrar tickers muy comunes que no son criptomonedas
            excluded = {'USD', 'USDT', 'THE', 'AND', 'FOR', 'YOU', 'ARE', 'CAN', 'NOT', 'BUT', 'ALL', 'NEW', 'GET', 'NOW', 'OUT', 'WAY', 'WHO', 'OIL', 'BOT', 'API', 'CEO', 'ATH', 'ATL', 'DCA', 'HOT', 'TOP', 'LOW', 'BIG', 'BAD', 'GOD'}
            
            if match not in excluded and match not in found_tickers:
                # Verificar que no sea una palabra común en inglés
                if len(match) >= 3 and not match.lower() in ['buy', 'sell', 'hold', 'pump', 'dump', 'moon', 'bear', 'bull', 'long', 'short']:
                    found_tickers.append(match)
    
    return found_tickers

def scan_subreddit_for_hype(subreddit_name: str, time_window_hours: int = 1) -> Dict[str, Any]:
    """
    Escanea un subreddit específico buscando menciones de tickers en posts recientes.
    
    Args:
        subreddit_name: Nombre del subreddit a escanear
        time_window_hours: Ventana de tiempo en horas para considerar posts "recientes"
        
    Returns:
        Dict con estadísticas de menciones encontradas
    """
    try:
        reddit = get_reddit_instance()
        subreddit = reddit.subreddit(subreddit_name)
        
        # Calcular tiempo límite
        time_limit = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        ticker_mentions = Counter()
        posts_analyzed = 0
        posts_with_mentions = 0
        
        logger.info(f"🔍 Escaneando r/{subreddit_name} (últimas {time_window_hours}h)...")
        
        # Analizar posts nuevos y calientes
        for post_source in [subreddit.new(limit=50), subreddit.hot(limit=25)]:
            for submission in post_source:
                # Verificar que el post sea reciente
                post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if post_time < time_limit:
                    continue
                
                posts_analyzed += 1
                
                # Extraer tickers del título
                found_tickers = extract_tickers_from_text(submission.title)
                
                if found_tickers:
                    posts_with_mentions += 1
                    for ticker in found_tickers:
                        ticker_mentions[ticker] += 1
                        logger.debug(f"📈 Encontrado {ticker} en: {submission.title[:50]}...")
        
        result = {
            'subreddit': subreddit_name,
            'time_window_hours': time_window_hours,
            'posts_analyzed': posts_analyzed,
            'posts_with_mentions': posts_with_mentions,
            'ticker_mentions': dict(ticker_mentions),
            'top_tickers': dict(ticker_mentions.most_common(10)),
            'scan_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ r/{subreddit_name}: {posts_analyzed} posts, {posts_with_mentions} con menciones, {len(ticker_mentions)} tickers únicos")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 Error escaneando r/{subreddit_name}: {e}")
        return {
            'subreddit': subreddit_name,
            'error': str(e),
            'scan_timestamp': datetime.now(timezone.utc).isoformat()
        }

def run_full_hype_scan(time_window_hours: int = 1) -> Dict[str, Any]:
    """
    Ejecuta un escaneo completo de todos los subreddits de hype.
    
    Args:
        time_window_hours: Ventana de tiempo en horas para el análisis
        
    Returns:
        Dict con resultados agregados del escaneo
    """
    try:
        # Verificar credenciales
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("⚠️ No se han configurado las credenciales de Reddit")
            return {"success": False, "error": "Credenciales de Reddit no configuradas"}
        
        logger.info("🎯 Iniciando escaneo completo del Hype Radar...")
        logger.info(f"📡 Monitoreando {len(HYPE_SUBREDDITS)} subreddits de alto riesgo")
        logger.info(f"🎯 Lista principal: {len(TARGET_TICKERS)} tickers objetivo")
        logger.info(f"🔍 Detección inteligente: Cualquier ticker que supere umbral")
        logger.info(f"⏰ Ventana de tiempo: {time_window_hours} hora(s)")
        
        all_ticker_mentions = Counter()
        subreddit_results = []
        total_posts_analyzed = 0
        total_posts_with_mentions = 0
        
        # Escanear cada subreddit
        for subreddit_name in HYPE_SUBREDDITS:
            result = scan_subreddit_for_hype(subreddit_name, time_window_hours)
            subreddit_results.append(result)
            
            # Agregar a estadísticas globales
            if 'error' not in result:
                total_posts_analyzed += result['posts_analyzed']
                total_posts_with_mentions += result['posts_with_mentions']
                
                # Sumar menciones de tickers
                for ticker, count in result['ticker_mentions'].items():
                    all_ticker_mentions[ticker] += count
        
        # Preparar resultado final
        final_result = {
            'success': True,
            'scan_timestamp': datetime.now(timezone.utc).isoformat(),
            'time_window_hours': time_window_hours,
            'subreddits_scanned': len(HYPE_SUBREDDITS),
            'total_posts_analyzed': total_posts_analyzed,
            'total_posts_with_mentions': total_posts_with_mentions,
            'unique_tickers_mentioned': len(all_ticker_mentions),
            'all_ticker_mentions': dict(all_ticker_mentions),
            'top_trending_tickers': dict(all_ticker_mentions.most_common(15)),
            'subreddit_details': subreddit_results
        }
        
        # Log resumen
        logger.info("=" * 60)
        logger.info("🎯 RESUMEN DEL HYPE RADAR")
        logger.info(f"📊 Posts analizados: {total_posts_analyzed}")
        logger.info(f"📈 Posts con menciones: {total_posts_with_mentions}")
        logger.info(f"🎯 Tickers únicos detectados: {len(all_ticker_mentions)}")
        
        if all_ticker_mentions:
            logger.info("🔥 TOP 5 TICKERS MÁS MENCIONADOS:")
            for ticker, count in all_ticker_mentions.most_common(5):
                logger.info(f"   {ticker}: {count} menciones")
        
        logger.info("=" * 60)
        
        return final_result
        
    except Exception as e:
        logger.error(f"💥 Error en escaneo completo del hype radar: {e}")
        return {
            'success': False,
            'error': str(e),
            'scan_timestamp': datetime.now(timezone.utc).isoformat()
        }

# Función principal para integración con scheduler
def execute_hype_radar_scan(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Función principal para ejecutar el escaneo del hype radar.
    Esta función será llamada por el scheduler.
    
    Args:
        db: Sesión de base de datos (opcional, para futuras integraciones)
        
    Returns:
        Dict con resultados del escaneo
    """
    if db is None:
        db = SessionLocal()
        
    try:
        # Ejecutar escaneo completo
        result = run_full_hype_scan(time_window_hours=3)
        
        # Si el escaneo fue exitoso, analizar tendencias y enviar alertas
        if result.get('success', False):
            ticker_mentions = result.get('all_ticker_mentions', {})
            
            # Analizar tendencias usando el nuevo módulo de analytics
            from services.hype.core.hype_analytics import analyze_hype_trends
            from services.hype.core.notifications import send_hype_alert
            
            alerts_to_send = analyze_hype_trends(ticker_mentions)
            
            # Enviar alertas de hype si las hay
            alerts_sent = 0
            for alert_data in alerts_to_send:
                success = send_hype_alert(
                    ticker=alert_data['ticker'],
                    current_mentions=alert_data['current_mentions'],
                    avg_mentions=alert_data['avg_mentions'],
                    velocity_percent=alert_data['velocity_percent'],
                    threshold=alert_data['threshold']
                )
                if success:
                    alerts_sent += 1
            
            # Añadir información de alertas al resultado
            result['alerts_analyzed'] = len(alerts_to_send)
            result['alerts_sent'] = alerts_sent
            
            if alerts_sent > 0:
                logger.info(f"🚨 {alerts_sent} alertas de hype enviadas exitosamente")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 Error en execute_hype_radar_scan: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        if db:
            db.close()

def get_hype_trends_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene un resumen de las tendencias de hype detectadas.
    
    Args:
        hours: Número de horas a incluir en el resumen
        
    Returns:
        Dict con resumen detallado de tendencias
    """
    try:
        from services.hype.core.hype_analytics import get_hype_summary
        
        summary = get_hype_summary(hours)
        
        if summary:
            logger.info(f"📊 Resumen de {hours}h generado: {summary.get('total_tickers_tracked', 0)} tickers")
            return {
                'success': True,
                'summary': summary
            }
        else:
            return {
                'success': False,
                'error': 'No hay datos suficientes para generar resumen'
            }
            
    except Exception as e:
        logger.error(f"❌ Error generando resumen de tendencias: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def configure_hype_alerts(threshold_percent: float = 500.0) -> Dict[str, Any]:
    """
    Configura el umbral de alertas de hype.
    
    Args:
        threshold_percent: Nuevo umbral en porcentaje
        
    Returns:
        Dict con resultado de la configuración
    """
    try:
        from services.hype.core.hype_analytics import configure_hype_threshold
        
        configure_hype_threshold(threshold_percent)
        
        logger.info(f"⚙️ Umbral de hype configurado a {threshold_percent}%")
        return {
            'success': True,
            'new_threshold': threshold_percent,
            'message': f'Umbral actualizado a {threshold_percent}%'
        }
        
    except Exception as e:
        logger.error(f"❌ Error configurando umbral de hype: {e}")
        return {
            'success': False,
            'error': str(e)
        } 