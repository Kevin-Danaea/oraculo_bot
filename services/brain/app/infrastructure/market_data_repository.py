"""
Repositorio de Datos de Mercado
==============================

Implementación concreta del repositorio de datos de mercado.
"""

import logging
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import ccxt

from app.domain.interfaces import MarketDataRepository
from app.domain.entities import MarketIndicators
from shared.config.settings import settings

logger = logging.getLogger(__name__)


class BinanceMarketDataRepository(MarketDataRepository):
    """
    Implementación del repositorio de datos de mercado usando Binance.
    """
    
    def __init__(self):
        """Inicializa el repositorio."""
        self._exchange = None
        self.logger = logging.getLogger(__name__)
    
    def _get_exchange(self):
        """
        Obtiene la instancia del exchange Binance.
        
        Returns:
            Cliente ccxt configurado para Binance
        """
        if self._exchange is None:
            try:
                self._exchange = ccxt.binance({
                    'apiKey': settings.BINANCE_API_KEY,
                    'secret': settings.BINANCE_API_SECRET,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
            except Exception as e:
                self.logger.error(f"Error creando cliente Binance: {e}")
                raise
        return self._exchange
    
    async def fetch_market_data(
        self, 
        pair: str, 
        timeframe: str = '4h', 
        days: int = 40
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos históricos de mercado para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            timeframe: Marco temporal ('4h', '1h', '1d')
            days: Número de días de historial
            
        Returns:
            Datos de mercado o None si hay error
        """
        try:
            self.logger.info(f"📊 Obteniendo datos para {pair} ({timeframe}, {days} días)...")
            
            exchange = self._get_exchange()
            
            # Calcular timestamp de inicio
            since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
            
            # Obtener datos históricos
            ohlcv = exchange.fetch_ohlcv(pair, timeframe, since)
            
            if not ohlcv:
                self.logger.warning(f"No se obtuvieron datos para {pair}")
                return None
            
            # Crear DataFrame
            column_names = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df = pd.DataFrame(data=ohlcv, columns=pd.Index(column_names))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convertir a float64 para pandas-ta
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(np.float64)
            
            self.logger.info(f"✅ Obtenidos {len(df)} registros para {pair}")
            
            # Calcular indicadores técnicos
            df = self._calculate_technical_indicators(df)
            
            # Obtener datos de sentimiento
            df = await self._fetch_sentiment_data(df)
            
            # Convertir a diccionario
            market_data = {
                'pair': pair,
                'timeframe': timeframe,
                'data': df.to_dict('records'),
                'columns': df.columns.tolist(),
                'index': df.index.tolist(),
                'shape': df.shape
            }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos para {pair}: {e}")
            return None
    
    async def calculate_indicators(self, market_data: Dict[str, Any]) -> Optional[MarketIndicators]:
        """
        Calcula indicadores técnicos a partir de datos de mercado.
        
        Args:
            market_data: Datos de mercado
            
        Returns:
            Indicadores calculados o None si hay error
        """
        try:
            if not market_data or 'data' not in market_data:
                return None
            
            # Recrear DataFrame
            df = pd.DataFrame(market_data['data'])
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Obtener valores actuales (última fila)
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            
            # Extraer indicadores con manejo de None
            adx_value = float(latest.get('ADX_14', 0)) if pd.notna(latest.get('ADX_14')) else 0.0
            volatility_value = float(latest.get('BBW_20_2.0', 0)) if pd.notna(latest.get('BBW_20_2.0')) else 0.0
            sentiment_value = float(latest.get('sentiment_promedio', 0)) if pd.notna(latest.get('sentiment_promedio')) else None
            rsi_value = float(latest.get('RSI_14', 0)) if pd.notna(latest.get('RSI_14')) else 0.0
            macd_value = float(latest.get('MACD_12_26_9', 0)) if pd.notna(latest.get('MACD_12_26_9')) else 0.0
            ema21_value = float(latest.get('EMA_21', 0)) if pd.notna(latest.get('EMA_21')) else 0.0
            ema50_value = float(latest.get('EMA_50', 0)) if pd.notna(latest.get('EMA_50')) else 0.0
            
            indicators = MarketIndicators(
                adx=adx_value,
                volatility=volatility_value,
                sentiment=sentiment_value,
                rsi=rsi_value,
                macd=macd_value,
                ema21=ema21_value,
                ema50=ema50_value,
                timestamp=datetime.utcnow()
            )
            
            self.logger.info(f"✅ Indicadores calculados para {market_data.get('pair', 'unknown')}")
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores: {e}")
            return None
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos en el DataFrame usando pandas-ta.
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores añadidos
        """
        try:
            # ADX (Average Directional Index)
            df['ADX_14'] = ta.adx(df['high'], df['low'], df['close'], length=14)
            
            # Bandas de Bollinger
            bb = ta.bbands(df['close'], length=20, std=2)
            df['BBL_20_2.0'] = bb['BBL_20_2.0']  # Lower
            df['BBM_20_2.0'] = bb['BBM_20_2.0']  # Middle
            df['BBU_20_2.0'] = bb['BBU_20_2.0']  # Upper
            df['BBW_20_2.0'] = bb['BBW_20_2.0']  # Width (volatilidad)
            
            # RSI
            df['RSI_14'] = ta.rsi(df['close'], length=14)
            
            # MACD
            macd = ta.macd(df['close'])
            df['MACD_12_26_9'] = macd['MACD_12_26_9']
            df['MACDs_12_26_9'] = macd['MACDs_12_26_9']
            df['MACDh_12_26_9'] = macd['MACDh_12_26_9']
            
            # EMA 21 y 50
            df['EMA_21'] = ta.ema(df['close'], length=21)
            df['EMA_50'] = ta.ema(df['close'], length=50)
            
            self.logger.debug("✅ Indicadores técnicos calculados con pandas-ta")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores técnicos: {e}")
            return df
    
    async def _fetch_sentiment_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Obtiene datos de sentimiento de la base de datos.
        
        Args:
            df: DataFrame con datos de precios
            
        Returns:
            DataFrame con datos de sentimiento agregados
        """
        try:
            from shared.database.session import SessionLocal
            from sqlalchemy import text
            
            self.logger.info("📰 Obteniendo datos de sentimiento de la base de datos...")
            
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
                    sentiment_df = pd.DataFrame(sentiment_data, columns=pd.Index(['fecha', 'sentiment_daily', 'num_noticias']))
                    sentiment_df['fecha'] = pd.to_datetime(sentiment_df['fecha'])
                    sentiment_df['date_only'] = sentiment_df['fecha'].dt.date
                    
                    # Preparar DataFrame de precios con columna auxiliar de fecha
                    df_reset = df.reset_index()
                    df_reset['date_only'] = df_reset['timestamp'].dt.date if 'timestamp' in df_reset.columns else df_reset['index'].dt.date
                    
                    # Hacer merge por fecha
                    df_merged = pd.merge(
                        df_reset,
                        sentiment_df[['date_only', 'sentiment_daily', 'num_noticias']],
                        on='date_only',
                        how='left'
                    )
                    
                    # Calcular promedio móvil de sentimiento (7 días)
                    df_merged['sentiment_promedio'] = df_merged['sentiment_daily'].rolling(window=7, min_periods=1).mean()
                    
                    # Restaurar índice
                    df_merged.set_index('timestamp' if 'timestamp' in df_merged.columns else 'index', inplace=True)
                    df_merged.drop(['date_only'], axis=1, inplace=True)
                    
                    self.logger.info(f"✅ Datos de sentimiento agregados: {len(sentiment_data)} días")
                    
                    return df_merged
                else:
                    self.logger.warning("⚠️ No se encontraron datos de sentimiento")
                    # Agregar columna vacía
                    df['sentiment_promedio'] = None
                    return df
                    
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de sentimiento: {e}")
            # Agregar columna vacía en caso de error
            df['sentiment_promedio'] = None
            return df 