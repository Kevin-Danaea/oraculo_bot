"""Use case for analyzing market conditions and generating trading signals."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from ..domain.entities import TrendSignal, TrendStrategy, MarketConditions
from ..domain.interfaces import ITrendAnalyzer, ITrendRepository, INotificationService

logger = logging.getLogger(__name__)


class AnalyzeMarketUseCase:
    """Caso de uso para analizar el mercado y generar señales de trading."""
    
    def __init__(
        self,
        trend_analyzer: ITrendAnalyzer,
        repository: ITrendRepository,
        notification_service: INotificationService
    ):
        self.trend_analyzer = trend_analyzer
        self.repository = repository
        self.notification_service = notification_service
        
    async def execute(self, symbol: Optional[str] = None) -> List[TrendSignal]:
        """
        Analiza el mercado para los símbolos configurados y genera señales.
        
        Args:
            symbol: Símbolo específico a analizar (opcional)
            
        Returns:
            Lista de señales generadas
        """
        try:
            # Obtener estrategias activas
            if symbol:
                strategy = await self.repository.get_strategy(symbol)
                strategies = [strategy] if strategy and strategy.enabled else []
            else:
                strategies = await self.repository.get_all_strategies(enabled_only=True)
            
            if not strategies:
                logger.info("No hay estrategias activas para analizar")
                return []
            
            all_signals = []
            
            for strategy in strategies:
                try:
                    # Analizar condiciones del mercado
                    market_conditions = await self.trend_analyzer.analyze_trend(
                        symbol=strategy.symbol,
                        timeframe=strategy.analysis_timeframe
                    )
                    
                    logger.info(
                        f"Condiciones del mercado para {strategy.symbol}: "
                        f"Tendencia={market_conditions.trend.value}, "
                        f"Volatilidad={market_conditions.volatility:.2f}, "
                        f"Fuerza={market_conditions.strength_index:.1f}"
                    )
                    
                    # Verificar si hay señales activas recientes
                    active_signals = await self.repository.get_active_signals(strategy.symbol)
                    recent_signal = self._has_recent_signal(active_signals)
                    
                    if recent_signal:
                        logger.debug(
                            f"Ya existe una señal reciente para {strategy.symbol}, "
                            "esperando antes de generar nueva señal"
                        )
                        continue
                    
                    # Generar señal si las condiciones son favorables
                    signal = await self.trend_analyzer.generate_signal(
                        symbol=strategy.symbol,
                        strategy=strategy,
                        market_conditions=market_conditions
                    )
                    
                    if signal:
                        # Validar la señal
                        if self._validate_signal(signal, strategy):
                            # Guardar la señal
                            await self.repository.save_signal(signal)
                            
                            # Notificar sobre la nueva señal
                            await self.notification_service.send_signal_alert(signal)
                            
                            all_signals.append(signal)
                            logger.info(
                                f"Nueva señal generada para {strategy.symbol}: "
                                f"{signal.direction.value} a {signal.entry_price} "
                                f"con confianza {signal.confidence:.2%}"
                            )
                        else:
                            logger.debug(
                                f"Señal para {strategy.symbol} no pasó validación"
                            )
                    
                except Exception as e:
                    logger.error(
                        f"Error analizando {strategy.symbol}: {str(e)}",
                        exc_info=True
                    )
                    await self.notification_service.send_error_alert(
                        f"Error en análisis de {strategy.symbol}",
                        {"error": str(e)}
                    )
                    
            return all_signals
            
        except Exception as e:
            logger.error(f"Error en análisis de mercado: {str(e)}", exc_info=True)
            await self.notification_service.send_error_alert(
                "Error crítico en análisis de mercado",
                {"error": str(e)}
            )
            return []
    
    def _has_recent_signal(
        self, 
        signals: List[TrendSignal], 
        cooldown_minutes: int = 30
    ) -> bool:
        """Verifica si hay una señal reciente dentro del período de cooldown."""
        if not signals:
            return False
            
        cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        
        for signal in signals:
            if signal.is_valid() and signal.timestamp > cutoff_time:
                return True
                
        return False
    
    def _validate_signal(self, signal: TrendSignal, strategy: TrendStrategy) -> bool:
        """Valida que la señal cumpla con los criterios de la estrategia."""
        # Verificar fuerza mínima de señal
        if signal.strength.value < strategy.min_signal_strength.value:
            logger.debug(
                f"Señal rechazada: fuerza {signal.strength.value} < "
                f"mínima {strategy.min_signal_strength.value}"
            )
            return False
        
        # Verificar confianza mínima
        if signal.confidence < strategy.min_confidence:
            logger.debug(
                f"Señal rechazada: confianza {signal.confidence:.2%} < "
                f"mínima {strategy.min_confidence:.2%}"
            )
            return False
        
        # Verificar ratio riesgo/recompensa
        risk_reward = signal.risk_reward_ratio()
        min_risk_reward = 1.5  # Mínimo 1.5:1
        
        if risk_reward < min_risk_reward:
            logger.debug(
                f"Señal rechazada: ratio R/R {risk_reward:.2f} < "
                f"mínimo {min_risk_reward}"
            )
            return False
        
        return True 