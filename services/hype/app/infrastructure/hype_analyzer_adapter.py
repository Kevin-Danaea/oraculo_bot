"""
Adaptador de infraestructura para el análisis de tendencias de Hype.
"""
from typing import Dict, List, Any
from datetime import datetime
import threading

from shared.services.logging_config import get_logger
from app.domain.interfaces import HypeAnalyzer

logger = get_logger(__name__)

class VolumeHypeAnalyzer:
    """
    Analizador de tendencias de hype que evalúa el volumen de menciones
    en las últimas 24 horas y genera alertas si supera un umbral.
    Mantiene el estado interno para cooldowns y resúmenes.
    """
    def __init__(self):
        self.last_alert_timestamp: Dict[str, datetime] = {}
        self.lock = threading.Lock()
        self.min_mentions_for_alert = 25  # Umbral por defecto
        self.alert_cooldown_hours = 4     # Cooldown por defecto

        logger.info("🔬 VolumeHypeAnalyzer inicializado (Modo Volumen)")
        self._log_config()

    def _log_config(self):
        logger.info(f"⚙️ Configuración: Umbral Menciones={self.min_mentions_for_alert}, Cooldown={self.alert_cooldown_hours}h")

    def _should_send_alert(self, ticker: str) -> bool:
        """Determina si se debe enviar una alerta considerando el cooldown."""
        with self.lock:
            now = datetime.now()
            last_alert_time = self.last_alert_timestamp.get(ticker)
            
            if last_alert_time:
                if (now - last_alert_time).total_seconds() < self.alert_cooldown_hours * 3600:
                    logger.debug(f"🔇 Alerta para ${ticker} en cooldown.")
                    return False
            
            self.last_alert_timestamp[ticker] = now
            return True
    
    def analyze(self, ticker_mentions_24h: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Analiza los tickers por volumen de menciones en 24h y retorna una lista de alertas.
        """
        alerts_to_send = []
        
        for ticker, total_mentions in ticker_mentions_24h.items():
            if total_mentions >= self.min_mentions_for_alert:
                if self._should_send_alert(ticker):
                    alert_data = {
                        'ticker': ticker,
                        'total_mentions_24h': total_mentions,
                        'threshold': self.min_mentions_for_alert,
                    }
                    alerts_to_send.append(alert_data)
                    logger.info(f"🚨 ALERTA DE HYPE (VOLUMEN): ${ticker} - {total_mentions} menciones (Umbral: {self.min_mentions_for_alert})")
        
        if alerts_to_send:
            logger.info(f"📢 {len(alerts_to_send)} alertas de hype por volumen preparadas para envío")
            
        return alerts_to_send

    def set_threshold(self, new_threshold: int):
        """Configura un nuevo umbral de menciones."""
        with self.lock:
            logger.info(f"🔧 Actualizando umbral de hype a {new_threshold} menciones")
            self.min_mentions_for_alert = new_threshold
            self._log_config()

# --- Instancia Singleton del Analizador ---
# Usamos un singleton para que el estado (cooldowns) se mantenga a través de la aplicación.
volume_analyzer_instance = VolumeHypeAnalyzer()

class HypeAnalyzerAdapter(HypeAnalyzer):
    """
    Implementación de la interfaz HypeAnalyzer que utiliza el VolumeHypeAnalyzer.
    """
    def analyze_mentions(self, ticker_mentions: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Delega el análisis al singleton del analizador de volumen.
        """
        return volume_analyzer_instance.analyze(ticker_mentions)
    
    def configure_threshold(self, new_threshold: int) -> None:
        """
        Delega la configuración del umbral al singleton.
        """
        volume_analyzer_instance.set_threshold(new_threshold) 