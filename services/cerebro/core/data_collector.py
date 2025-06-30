"""
Data Collector - Recolección y Preparación de Datos de Mercado
============================================================

Módulo para recolectar datos históricos de Binance y calcular
indicadores técnicos para el motor de decisiones.
"""

import logging
import pandas as pd
import numpy as np
import talib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import ccxt
from shared.config.settings import settings

logger = logging.getLogger(__name__)

def get_binance_client():
    """
    Crea y retorna un cliente de Binance configurado.
    
    Returns:
        Cliente ccxt configurado para Binance
    """
    try:
        exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'sandbox': False,  # Cambiar a True para modo sandbox
            'enableRateLimit': True,
        })
        return exchange
    except Exception as e:
        logger.error(f"Error creando cliente Binance: {e}")
        raise

def fetch_and_prepare_data(
    symbol: str, 
    timeframe: str = '4h', 
    days: int = 40
) -> Optional[pd.DataFrame]:
    """
    Obtiene datos históricos de Binance y calcula indicadores técnicos.
    
    Args:
        symbol: Par de trading (ej: 'ETH/USDT')
        timeframe: Marco temporal ('4h', '1h', '1d')
        days: Número de días de historial a obtener
        
    Returns:
        DataFrame con datos OHLCV e indicadores calculados
    """
    try:
        logger.info(f"📊 Obteniendo datos para {symbol} ({timeframe}, {days} días)...")
        
        # Crear cliente Binance
        exchange = get_binance_client()
        
        # Calcular timestamp de inicio
        since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
        
        # Obtener datos históricos
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
        
        if not ohlcv:
            logger.warning(f"No se obtuvieron datos para {symbol}")
            return None
        
        # Crear DataFrame
        column_names = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df = pd.DataFrame(data=ohlcv, columns=column_names)  # type: ignore
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convertir a float64 para talib
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(np.float64)
        
        logger.info(f"✅ Obtenidos {len(df)} registros para {symbol}")
        
        # Calcular indicadores técnicos
        df = calculate_technical_indicators(df)
        
        # Obtener datos reales de sentimiento de la base de datos
        df = fetch_sentiment_data(df)
        
        logger.info(f"✅ Indicadores calculados para {symbol}")
        
        logger.info(f"✅ Indicadores calculados para {symbol}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos para {symbol}: {e}")
        return None

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores técnicos en el DataFrame usando TA-Lib.
    
    Args:
        df: DataFrame con datos OHLCV
        
    Returns:
        DataFrame con indicadores añadidos
    """
    try:
        # ADX (Average Directional Index)
        df['adx'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)  # type: ignore
        
        # Bandas de Bollinger
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2)  # type: ignore
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        # Ancho de Bandas de Bollinger (bb_width) - medida de volatilidad
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # RSI adicional (útil para análisis)
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)  # type: ignore
        
        # MACD
        macd, macd_signal, macd_hist = talib.MACD(df['close'].values)  # type: ignore
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_hist'] = macd_hist
        
        # EMA 21 y 50
        df['ema21'] = talib.EMA(df['close'].values, timeperiod=21)  # type: ignore
        df['ema50'] = talib.EMA(df['close'].values, timeperiod=50)  # type: ignore
        
        logger.debug("✅ Indicadores técnicos calculados con TA-Lib")
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculando indicadores técnicos: {e}")
        return df

def fetch_sentiment_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Obtiene datos reales de sentimiento de la base de datos de Neon.
    
    Args:
        df: DataFrame con datos de precios
        
    Returns:
        DataFrame con datos de sentimiento agregados
    """
    try:
        from shared.database.session import SessionLocal
        from sqlalchemy import text
        
        logger.info("📰 Obteniendo datos de sentimiento de la base de datos...")
        
        # Crear sesión de base de datos
        db = SessionLocal()
        
        try:
            # Obtener fechas de inicio y fin del DataFrame
            start_date = df.index.min()
            end_date = df.index.max()
            
            # Query para obtener datos de sentimiento
            query = text("""
                SELECT 
                    DATE(CAST(published_at AS TIMESTAMP)) as fecha,
                    AVG(sentiment_score) as sentiment_daily,
                    COUNT(*) as num_noticias
                FROM noticias 
                WHERE CAST(published_at AS TIMESTAMP) BETWEEN :start_date AND :end_date
                GROUP BY DATE(CAST(published_at AS TIMESTAMP))
                ORDER BY fecha
            """)
            
            result = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            
            sentiment_data = result.fetchall()
            
            if sentiment_data:
                # Crear DataFrame de sentimiento
                sentiment_df = pd.DataFrame(sentiment_data, columns=['fecha', 'sentiment_daily', 'num_noticias'])  # type: ignore
                sentiment_df['fecha'] = pd.to_datetime(sentiment_df['fecha'])
                sentiment_df['date_only'] = sentiment_df['fecha'].dt.date
                
                # Preparar DataFrame de precios con columna auxiliar de fecha
                df_reset = df.reset_index()
                df_reset['date_only'] = df_reset['timestamp'].dt.date if 'timestamp' in df_reset.columns else df_reset['index'].dt.date
                
                # Hacer merge por fecha (date_only)
                df_merged = pd.merge(
                    df_reset,
                    sentiment_df[['date_only', 'sentiment_daily', 'num_noticias']],
                    on='date_only',
                    how='left'
                )
                
                # Rellenar valores faltantes
                df_merged['sentiment_daily'] = df_merged['sentiment_daily'].fillna(0.0)
                df_merged['num_noticias'] = df_merged['num_noticias'].fillna(0)
                
                # Calcular media móvil de 7 días
                df_merged['sentiment_ma7'] = df_merged['sentiment_daily'].rolling(window=7, min_periods=1).mean()
                df_merged['sentiment_ma7'] = df_merged['sentiment_ma7'].fillna(0.0)
                
                # Restaurar índice original de precios
                if 'timestamp' in df_merged.columns:
                    df_merged.set_index('timestamp', inplace=True)
                elif 'index' in df_merged.columns:
                    df_merged.set_index('index', inplace=True)
                # Eliminar columna auxiliar
                if 'date_only' in df_merged.columns:
                    df_merged.drop(['date_only'], axis=1, inplace=True)
                
                logger.info(f"✅ Datos de sentimiento obtenidos: {len(sentiment_data)} días con noticias")
                logger.info(f"📊 Rango de sentimiento: {df_merged['sentiment_daily'].min():.3f} a {df_merged['sentiment_daily'].max():.3f}")
                logger.info(f"📈 Media móvil actual: {df_merged['sentiment_ma7'].iloc[-1]:.3f}")
                
                return df_merged
            else:
                logger.warning("⚠️ No se encontraron datos de sentimiento en la base de datos")
                # Crear columnas vacías
                df['sentiment_daily'] = 0.0
                df['sentiment_ma7'] = 0.0
                df['num_noticias'] = 0
                return df
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de sentimiento: {e}")
        # En caso de error, crear columnas con valores por defecto
        df['sentiment_daily'] = 0.0
        df['sentiment_ma7'] = 0.0
        df['num_noticias'] = 0
        return df


def generate_mock_sentiment(length: int) -> pd.Series:
    """
    Genera datos mock de sentiment para pruebas.
    En producción, esto se obtendría de la base de datos.
    
    Args:
        length: Número de valores a generar
        
    Returns:
        Serie con valores de sentiment entre -1 y 1
    """
    # Generar sentiment simulado con tendencia y ruido
    np.random.seed(42)  # Para reproducibilidad
    trend = np.linspace(-0.2, 0.3, length)  # Tendencia gradual
    noise = np.random.normal(0, 0.1, length)  # Ruido aleatorio
    sentiment = np.clip(trend + noise, -1, 1)  # Mantener en rango [-1, 1]
    
    return pd.Series(sentiment)

def get_current_indicators(df: pd.DataFrame) -> Dict[str, float]:
    """
    Extrae los valores actuales (más recientes) de los indicadores.
    
    Args:
        df: DataFrame con datos e indicadores
        
    Returns:
        Diccionario con indicadores actuales
    """
    if df is None or df.empty:
        return {}
    
    try:
        # Obtener la última fila válida (sin NaN en ADX)
        last_valid_idx = df['adx'].last_valid_index()
        if last_valid_idx is None:
            logger.warning("No se encontraron valores válidos de ADX")
            return {}
        
        last_row = df.loc[last_valid_idx]
        
        indicators = {
            'adx_actual': last_row['adx'],
            'volatilidad_actual': last_row['bb_width'],
            'sentiment_promedio': last_row['sentiment_ma7'],
            'precio_actual': last_row['close'],
            'rsi_actual': last_row['rsi'],
            'timestamp': last_valid_idx
        }
        
        # Filtrar NaN values
        indicators = {k: v for k, v in indicators.items() if pd.notna(v)}
        
        logger.debug(f"Indicadores actuales extraídos: {indicators}")
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error extrayendo indicadores actuales: {e}")
        return {} 