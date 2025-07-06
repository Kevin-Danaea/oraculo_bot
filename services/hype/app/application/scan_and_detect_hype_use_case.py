"""
Caso de uso principal para escanear todas las fuentes, analizar el hype,
notificar si es necesario y guardar los resultados.
"""
from collections import Counter
from typing import List, Dict, Any

from app.domain.interfaces import (
    HypeCollector, HypeRepository, NotificationService, HypeAnalyzer
)
from app.domain.entities import HypeScan, TickerMention, HypeEvent
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class ScanAndDetectHypeUseCase:
    """
    Orquesta el proceso completo de escaneo de hype, desde la recolección
    de datos hasta el análisis, notificación y persistencia.
    """
    def __init__(
        self,
        hype_collector: HypeCollector,
        hype_analyzer: HypeAnalyzer,
        hype_repository: HypeRepository,
        notification_service: NotificationService,
    ):
        self.hype_collector = hype_collector
        self.hype_analyzer = hype_analyzer
        self.hype_repository = hype_repository
        self.notification_service = notification_service
        logger.info("✅ ScanAndDetectHypeUseCase inicializado.")

    def execute(self, subreddits_to_scan: List[str], save_scan_result: bool = True):
        """
        Ejecuta el ciclo completo de detección de hype.
        
        Args:
            subreddits_to_scan: Lista de nombres de subreddits a escanear.
            save_scan_result: Si es True, guarda el resultado completo del escaneo.
        """
        logger.info(f"🚀 Iniciando ciclo de detección de hype para {len(subreddits_to_scan)} subreddits...")
        
        # 1. Recolectar datos de todas las fuentes (subreddits)
        all_posts = []
        for subreddit in subreddits_to_scan:
            all_posts.extend(self.hype_collector.collect_posts(subreddit))
        
        # 2. Extraer y contar menciones de tickers
        ticker_counts = Counter()
        for post in all_posts:
            tickers = self.hype_collector.extract_tickers_from_text(post.title)
            for ticker in tickers:
                ticker_counts[ticker] += 1
        
        logger.info(f"📊 Menciones contadas: {len(ticker_counts)} tickers únicos.")
        
        # 3. Analizar menciones para encontrar alertas
        alerts_to_send = self.hype_analyzer.analyze_mentions(dict(ticker_counts))
        
        # 4. Procesar y enviar alertas
        if alerts_to_send:
            logger.info(f"🚨 Se encontraron {len(alerts_to_send)} alertas de hype.")
            for alert_data in alerts_to_send:
                event = HypeEvent(**alert_data)
                
                # Enviar notificación y actualizar estado del evento
                alert_sent_successfully = self.notification_service.send_alert(event)
                event.alert_sent = alert_sent_successfully
                
                # Guardar el evento de hype en la base de datos
                self.hype_repository.save_event(event)
        
        # 5. Guardar el resultado completo del escaneo si se solicita
        if save_scan_result:
            logger.info("💾 Guardando resultado completo del escaneo...")
            scan_result = HypeScan(
                subreddits_scanned=len(subreddits_to_scan),
                posts_analyzed=len(all_posts),
                total_posts_with_mentions=sum(1 for post in all_posts if self.hype_collector.extract_tickers_from_text(post.title)),
                unique_tickers_mentioned=len(ticker_counts),
                top_trending_tickers=dict(ticker_counts.most_common(10)),
                mentions=[TickerMention(ticker=t, count=c) for t, c in ticker_counts.items()]
            )
            self.hype_repository.save_scan(scan_result)
        
        logger.info("✅ Ciclo de detección de hype finalizado.") 