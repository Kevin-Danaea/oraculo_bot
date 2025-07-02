"""
Hype Analytics Module - Análisis de Volumen de Menciones
==========================================================

Módulo especializado en analizar el volumen de menciones de tickers
para detectar tendencias basadas en un umbral absoluto en una ventana de 24 horas.
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from shared.services.logging_config import get_logger

logger = get_logger(__name__)

# --- Configuración del Modelo de Hype por Volumen ---
MIN_MENTIONS_FOR_ALERT = 25  # Mínimo de menciones en 24h para generar una alerta
ALERT_COOLDOWN_HOURS = 4     # Horas de cooldown para no repetir alerta del mismo ticker

class HypeTrendAnalyzer:
    """
    Analizador de tendencias de hype que evalúa el volumen de menciones
    en las últimas 24 horas y genera alertas si supera un umbral.
    Mantiene el último resultado del escaneo para los resúmenes diarios.
    """
    
    def __init__(self):
        """Inicializa el analizador con estructuras de datos para cooldown y resúmenes."""
        self.last_alert_timestamp = defaultdict(lambda: None)  # Cooldown para evitar spam
        self.total_alerts_sent = 0
        self.last_scan_mentions = {}  # Almacena el resultado del último escaneo
        self.lock = threading.Lock()  # Para thread safety
        
        logger.info("🔬 HypeTrendAnalyzer inicializado (Modo Volumen)")
        logger.info(f"⚙️ Configuración: Umbral Menciones={MIN_MENTIONS_FOR_ALERT}, Cooldown={ALERT_COOLDOWN_HOURS}h")

    def _should_send_alert(self, ticker: str) -> bool:
        """Determina si debe enviar una alerta considerando el cooldown."""
        now = datetime.now()
        last_alert_time = self.last_alert_timestamp.get(ticker)
        
        if last_alert_time:
            if (now - last_alert_time).total_seconds() < ALERT_COOLDOWN_HOURS * 3600:
                logger.debug(f"🔇 Alerta para ${ticker} en cooldown.")
                return False
        
        self.last_alert_timestamp[ticker] = now
        return True
    
    def analyze_tickers_by_volume(self, ticker_mentions_24h: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Analiza los tickers por volumen de menciones en 24h y retorna una lista de alertas.
        
        Args:
            ticker_mentions_24h: Menciones de las últimas 24 horas por ticker.
            
        Returns:
            List[Dict]: Lista de alertas con información detallada.
        """
        alerts_to_send = []
        
        with self.lock:
            try:
                # Almacenar los datos del escaneo actual para el resumen
                self.last_scan_mentions = ticker_mentions_24h

                # Analizar cada ticker con menciones actuales
                for ticker, total_mentions in ticker_mentions_24h.items():
                    if total_mentions >= MIN_MENTIONS_FOR_ALERT:
                        if self._should_send_alert(ticker):
                            alert_data = {
                                'ticker': ticker,
                                'total_mentions_24h': total_mentions,
                                'threshold': MIN_MENTIONS_FOR_ALERT,
                                'timestamp': datetime.now()
                            }
                            alerts_to_send.append(alert_data)
                            logger.info(f"🚨 ALERTA DE HYPE (VOLUMEN): ${ticker} - {total_mentions} menciones en 24h (Umbral: {MIN_MENTIONS_FOR_ALERT})")
                
                if alerts_to_send:
                    self.total_alerts_sent += len(alerts_to_send)
                    logger.info(f"📢 {len(alerts_to_send)} alertas de hype por volumen preparadas para envío")
                
                return alerts_to_send
                
            except Exception as e:
                logger.error(f"❌ Error analizando tickers por volumen: {e}")
                return []

    def get_trending_summary(self) -> Dict[str, Any]:
        """
        Genera un resumen de las tendencias basado en el último escaneo.
        Mantiene la compatibilidad con el job del scheduler diario.
        """
        with self.lock:
            try:
                if not self.last_scan_mentions:
                    return { 'top_5': {}, 'total_alerts_sent': self.total_alerts_sent }

                sorted_trending = dict(sorted(self.last_scan_mentions.items(), key=lambda x: x[1], reverse=True))
                
                return {
                    'period_hours': 24, # La ventana de datos es siempre 24h
                    'trending_tickers': sorted_trending,
                    'top_5': dict(list(sorted_trending.items())[:5]),
                    'total_alerts_sent': self.total_alerts_sent,
                    'timestamp': datetime.now()
                }
            except Exception as e:
                logger.error(f"❌ Error generando resumen de tendencias: {e}")
                return {}

    def reset_alert_counters(self) -> None:
        """Reinicia los contadores de alertas y cooldowns (útil para resúmenes diarios)."""
        with self.lock:
            self.total_alerts_sent = 0
            self.last_alert_timestamp.clear()
            logger.info("🔄 Contadores de alertas y cooldown reiniciados")

# --- Instancia Global ---
hype_analyzer = HypeTrendAnalyzer()


# --- Funciones de Utilidad (Wrapper) ---
# Mantienen una API consistente para ser llamadas desde otros módulos.

def get_hype_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Función de utilidad para obtener el resumen de tendencias del analizador.
    El parámetro 'hours' se ignora, ya que el análisis siempre se basa en las últimas 24h.
    """
    return hype_analyzer.get_trending_summary()

def configure_hype_threshold(new_threshold: int) -> None:
    """Configura dinámicamente el umbral de menciones para alertas."""
    global MIN_MENTIONS_FOR_ALERT
    logger.info(f"🔧 Actualizando umbral de hype a {new_threshold} menciones")
    MIN_MENTIONS_FOR_ALERT = new_threshold

# Renombramos la función principal para que quede claro el modelo que usa.
# El servicio `hype_radar_service` deberá llamar a esta función.
analyze_and_alert_by_volume = hype_analyzer.analyze_tickers_by_volume 