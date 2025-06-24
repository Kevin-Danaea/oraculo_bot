"""
Hype Analytics Module - Análisis de Velocidad de Menciones
==========================================================

Módulo especializado en calcular la velocidad de menciones de tickers
comparando datos históricos para detectar tendencias emergentes.
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from shared.services.logging_config import get_logger

logger = get_logger(__name__)

# Configuración global para análisis de hype
HYPE_THRESHOLD = 500.0  # Porcentaje de incremento para generar alerta (500% por defecto)
MIN_MENTIONS_THRESHOLD = 3  # Mínimo de menciones para considerar un ticker
HISTORY_HOURS = 24  # Horas de historial a mantener

class HypeTrendAnalyzer:
    """
    Analizador de tendencias de hype que mantiene un historial de menciones
    y calcula velocidades para detectar aumentos significativos.
    """
    
    def __init__(self):
        """Inicializa el analizador con estructuras de datos vacías."""
        self.mention_history = defaultdict(lambda: deque(maxlen=HISTORY_HOURS))  # Historial por ticker
        self.alert_cooldown = defaultdict(int)  # Cooldown para evitar spam de alertas
        self.total_alerts_sent = 0
        self.lock = threading.Lock()  # Para thread safety
        
        logger.info("🔬 HypeTrendAnalyzer inicializado")
        logger.info(f"⚙️ Configuración: Umbral={HYPE_THRESHOLD}%, Historia={HISTORY_HOURS}h")
    
    def add_mention_data(self, ticker_mentions: Dict[str, int], timestamp: Optional[datetime] = None) -> None:
        """
        Añade datos de menciones al historial.
        
        Args:
            ticker_mentions: Diccionario con menciones por ticker de la última hora
            timestamp: Timestamp de los datos (por defecto: ahora)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        with self.lock:
            try:
                # Añadir datos al historial para cada ticker
                for ticker, mentions in ticker_mentions.items():
                    self.mention_history[ticker].append({
                        'timestamp': timestamp,
                        'mentions': mentions
                    })
                
                # Limpiar datos antiguos (más de HISTORY_HOURS horas)
                self._cleanup_old_data(timestamp)
                
                logger.debug(f"📊 Datos añadidos: {len(ticker_mentions)} tickers, timestamp: {timestamp}")
                
            except Exception as e:
                logger.error(f"❌ Error añadiendo datos de menciones: {e}")
    
    def _cleanup_old_data(self, current_time: datetime) -> None:
        """
        Limpia datos más antiguos que HISTORY_HOURS del historial.
        
        Args:
            current_time: Tiempo actual para calcular qué datos eliminar
        """
        cutoff_time = current_time - timedelta(hours=HISTORY_HOURS)
        
        for ticker in list(self.mention_history.keys()):
            # Filtrar datos antiguos
            history = self.mention_history[ticker]
            while history and history[0]['timestamp'] < cutoff_time:
                history.popleft()
            
            # Eliminar ticker si no tiene datos
            if not history:
                del self.mention_history[ticker]
    
    def calculate_mention_velocity(self, ticker: str, current_mentions: int) -> Tuple[float, float, bool]:
        """
        Calcula la velocidad de menciones para un ticker específico.
        
        Args:
            ticker: Símbolo del ticker
            current_mentions: Menciones en la última hora
            
        Returns:
            Tuple[average_mentions, velocity_percent, should_alert]:
                - average_mentions: Promedio de menciones en las últimas 24h
                - velocity_percent: Porcentaje de incremento vs. promedio
                - should_alert: Si debe generar una alerta
        """
        try:
            with self.lock:
                history = self.mention_history.get(ticker, deque())
                
                # Si no hay historial suficiente, no podemos calcular velocidad
                if len(history) < 3:  # Necesitamos al menos 3 puntos de datos
                    return 0.0, 0.0, False
                
                # Calcular promedio de menciones en las últimas 24h (excluyendo la hora actual)
                historical_mentions = [entry['mentions'] for entry in history]
                avg_mentions = sum(historical_mentions) / len(historical_mentions)
                
                # Evitar división por cero
                if avg_mentions == 0:
                    if current_mentions > MIN_MENTIONS_THRESHOLD:
                        # Si el promedio es 0 pero hay menciones actuales, es un aumento infinito
                        return 0.0, float('inf'), current_mentions >= MIN_MENTIONS_THRESHOLD
                    return 0.0, 0.0, False
                
                # Calcular porcentaje de incremento
                velocity_percent = ((current_mentions - avg_mentions) / avg_mentions) * 100
                
                # Determinar si debe alertar
                should_alert = (
                    velocity_percent >= HYPE_THRESHOLD and 
                    current_mentions >= MIN_MENTIONS_THRESHOLD and
                    self._should_send_alert(ticker)
                )
                
                logger.debug(f"📈 {ticker}: {current_mentions} menciones, promedio: {avg_mentions:.1f}, velocidad: {velocity_percent:.1f}%")
                
                return avg_mentions, velocity_percent, should_alert
                
        except Exception as e:
            logger.error(f"❌ Error calculando velocidad para {ticker}: {e}")
            return 0.0, 0.0, False
    
    def _should_send_alert(self, ticker: str) -> bool:
        """
        Determina si debe enviar una alerta considerando el cooldown.
        
        Args:
            ticker: Símbolo del ticker
            
        Returns:
            bool: True si debe enviar alerta
        """
        current_hour = datetime.now().hour
        last_alert_hour = self.alert_cooldown.get(ticker, -1)
        
        # Enviar alerta solo si no se envió en la última hora
        if current_hour != last_alert_hour:
            self.alert_cooldown[ticker] = current_hour
            return True
        
        return False
    
    def analyze_all_tickers(self, current_ticker_mentions: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Analiza todos los tickers actuales y retorna una lista de alertas a enviar.
        
        Args:
            current_ticker_mentions: Menciones actuales por ticker
            
        Returns:
            List[Dict]: Lista de alertas con información detallada
        """
        alerts_to_send = []
        
        try:
            # Añadir datos actuales al historial
            self.add_mention_data(current_ticker_mentions)
            
            # Analizar cada ticker con menciones actuales
            for ticker, current_mentions in current_ticker_mentions.items():
                if current_mentions < MIN_MENTIONS_THRESHOLD:
                    continue  # Saltar tickers con pocas menciones
                
                avg_mentions, velocity_percent, should_alert = self.calculate_mention_velocity(ticker, current_mentions)
                
                if should_alert:
                    alert_data = {
                        'ticker': ticker,
                        'current_mentions': current_mentions,
                        'avg_mentions': avg_mentions,
                        'velocity_percent': velocity_percent,
                        'threshold': HYPE_THRESHOLD,
                        'timestamp': datetime.now()
                    }
                    alerts_to_send.append(alert_data)
                    
                    logger.info(f"🚨 ALERTA GENERADA: ${ticker} - {velocity_percent:.1f}% de incremento")
            
            if alerts_to_send:
                self.total_alerts_sent += len(alerts_to_send)
                logger.info(f"📢 {len(alerts_to_send)} alertas preparadas para envío")
            
            return alerts_to_send
            
        except Exception as e:
            logger.error(f"❌ Error analizando tickers: {e}")
            return []
    
    def get_trending_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Genera un resumen de las tendencias en las últimas N horas.
        
        Args:
            hours: Número de horas a analizar
            
        Returns:
            Dict con resumen de tendencias
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            trending_data = defaultdict(int)
            
            with self.lock:
                # Sumar menciones por ticker en el período especificado
                for ticker, history in self.mention_history.items():
                    for entry in history:
                        if entry['timestamp'] >= cutoff_time:
                            trending_data[ticker] += entry['mentions']
            
            # Ordenar por menciones (descendente)
            sorted_trending = dict(sorted(trending_data.items(), key=lambda x: x[1], reverse=True))
            
            return {
                'period_hours': hours,
                'total_tickers_tracked': len(self.mention_history),
                'trending_tickers': sorted_trending,
                'top_5': dict(list(sorted_trending.items())[:5]),
                'total_alerts_sent': self.total_alerts_sent,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen de tendencias: {e}")
            return {}
    
    def reset_alert_counters(self) -> None:
        """Reinicia los contadores de alertas (útil para resúmenes diarios)."""
        with self.lock:
            self.total_alerts_sent = 0
            self.alert_cooldown.clear()
            logger.info("🔄 Contadores de alertas reiniciados")

# Instancia global del analizador
hype_analyzer = HypeTrendAnalyzer()

# Funciones de utilidad para uso externo
def analyze_hype_trends(ticker_mentions: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    Función principal para analizar tendencias de hype.
    
    Args:
        ticker_mentions: Diccionario con menciones actuales por ticker
        
    Returns:
        List[Dict]: Lista de alertas a enviar
    """
    return hype_analyzer.analyze_all_tickers(ticker_mentions)

def get_hype_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene un resumen de las tendencias detectadas.
    
    Args:
        hours: Horas a incluir en el resumen
        
    Returns:
        Dict con resumen de tendencias
    """
    return hype_analyzer.get_trending_summary(hours)

def configure_hype_threshold(new_threshold: float) -> None:
    """
    Configura el umbral global de alertas de hype.
    
    Args:
        new_threshold: Nuevo umbral en porcentaje (ej: 500.0 para 500%)
    """
    global HYPE_THRESHOLD
    HYPE_THRESHOLD = new_threshold
    logger.info(f"⚙️ Umbral de hype actualizado a {new_threshold}%") 