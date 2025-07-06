"""
Caso de uso para generar y enviar el resumen diario de tendencias de hype.
"""
from datetime import datetime
from typing import Dict, Any

from app.domain.interfaces import HypeRepository, NotificationService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class SendDailySummaryUseCase:
    """
    Genera y envía un resumen diario de las tendencias de hype detectadas.
    """
    
    def __init__(
        self,
        hype_repository: HypeRepository,
        notification_service: NotificationService
    ):
        self.hype_repository = hype_repository
        self.notification_service = notification_service
        logger.info("✅ SendDailySummaryUseCase inicializado.")

    def execute(self, hours: int = 24) -> Dict[str, Any]:
        """
        Ejecuta el envío del resumen diario.
        
        Args:
            hours: Número de horas hacia atrás para incluir en el resumen
            
        Returns:
            Dict con el resultado del envío del resumen
        """
        logger.info(f"📊 Iniciando generación de resumen diario ({hours}h)...")
        
        try:
            # Obtener eventos recientes de la base de datos (últimas 24h, máximo 100 eventos)
            recent_events = self.hype_repository.get_recent_events(hours, limit=100)
            
            # Generar estadísticas del resumen
            summary_stats = self._generate_summary_stats(recent_events, hours)
            
            # Enviar resumen por Telegram
            success = self.notification_service.send_daily_summary(summary_stats)
            
            if success:
                logger.info(f"✅ Resumen diario enviado exitosamente.")
                return {
                    'success': True,
                    'events_count': len(recent_events),
                    'summary_stats': summary_stats
                }
            else:
                logger.error("❌ Error enviando resumen diario.")
                return {
                    'success': False,
                    'error': 'Error enviando resumen por Telegram'
                }
                
        except Exception as e:
            logger.error(f"💥 Error inesperado generando resumen diario: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_summary_stats(self, events, hours: int) -> Dict[str, Any]:
        """
        Genera estadísticas resumidas a partir de los eventos recientes.
        """
        # Contar alertas por ticker
        ticker_alert_counts = {}
        total_alerts = len(events)
        
        for event in events:
            ticker = event.ticker
            if ticker in ticker_alert_counts:
                ticker_alert_counts[ticker] += 1
            else:
                ticker_alert_counts[ticker] = 1
        
        # Obtener top 5 tickers más alertados
        top_trending = dict(sorted(ticker_alert_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return {
            'period_hours': hours,
            'total_alerts_sent': total_alerts,
            'unique_tickers_alerted': len(ticker_alert_counts),
            'top_trending_tickers': top_trending,
            'timestamp': datetime.now()
        } 