"""
Caso de Uso: Análisis de Tendencia
==================================

Ejecuta análisis específico para la estrategia TREND.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.domain.interfaces import (
    MarketDataRepository, 
    DecisionRepository, 
    RecipeRepository,
    NotificationService
)
from app.domain.entities import (
    TradingDecision, 
    TrendDecision,
    BotType, 
    DecisionType, 
    MarketIndicators, 
    TradingThresholds,
    TrendPositionState
)

logger = logging.getLogger(__name__)


class AnalyzeTrendUseCase:
    """
    Caso de uso para análisis específico de estrategia TREND.
    """
    
    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        decision_repo: DecisionRepository,
        recipe_repo: RecipeRepository,
        notification_service: NotificationService
    ):
        """
        Inicializa el caso de uso.
        
        Args:
            market_data_repo: Repositorio de datos de mercado
            decision_repo: Repositorio de decisiones
            recipe_repo: Repositorio de recetas
            notification_service: Servicio de notificaciones
        """
        self.market_data_repo = market_data_repo
        self.decision_repo = decision_repo
        self.recipe_repo = recipe_repo
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, pair: str) -> Optional[TrendDecision]:
        """
        Ejecuta el análisis de tendencia para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            
        Returns:
            Decisión de tendencia o None si hay error
        """
        try:
            self.logger.info(f"📈 ========== ANÁLISIS TREND PARA {pair} ==========")
            
            # Obtener datos de mercado (timeframe 1d para tendencia)
            market_data = await self.market_data_repo.fetch_market_data(pair, timeframe='1d', days=200)
            if not market_data:
                self.logger.warning(f"⚠️ No se pudieron obtener datos para {pair}")
                return None
            
            # Calcular indicadores
            indicators = await self.market_data_repo.calculate_indicators(market_data)
            if not indicators:
                self.logger.warning(f"⚠️ No se pudieron calcular indicadores para {pair}")
                return None
            
            # Obtener receta para TREND
            recipe = await self.recipe_repo.get_recipe(pair, BotType.TREND)
            if not recipe:
                self.logger.warning(f"⚠️ No se encontró receta TREND para {pair}")
                return None
            
            # Obtener umbrales de la receta
            thresholds = recipe.get_thresholds()
            
            # Obtener estado actual de posición
            current_state = await self._get_current_position_state(pair)
            
            # Detectar señales de tendencia
            trend_signals = self._detect_trend_signals(indicators)
            
            # Tomar decisión basada en estado y señales
            decision = self._make_trend_decision(
                pair, 
                current_state, 
                indicators, 
                thresholds, 
                trend_signals
            )
            
            # Guardar decisión
            saved = await self.decision_repo.save_decision(decision)
            if saved:
                # Notificar cambio de decisión
                await self.notification_service.notify_decision_change(decision)
                
                self.logger.info(f"✅ {pair} TREND: {decision.decision.value} - {decision.reason}")
                return decision
            else:
                self.logger.error(f"❌ Error guardando decisión TREND para {pair}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error analizando TREND para {pair}: {e}")
            await self.notification_service.notify_error(
                f"Error analizando TREND para {pair}", 
                {"pair": pair, "error": str(e)}
            )
            return None
    
    async def _get_current_position_state(self, pair: str) -> TrendPositionState:
        """
        Obtiene el estado actual de posición para el par.
        Por defecto asume FUERA_DEL_MERCADO.
        
        Args:
            pair: Par de trading
            
        Returns:
            Estado actual de posición
        """
        try:
            # TODO: En el futuro, consultar el estado real del bot de tendencia
            # Por ahora, asumimos FUERA_DEL_MERCADO como estado inicial
            # Esto se puede mejorar consultando la base de datos o el servicio de tendencia
            
            # Buscar la última decisión para ver si hay una posición activa
            last_decision = await self.decision_repo.get_latest_decision(pair, BotType.TREND)
            
            if last_decision and last_decision.decision == DecisionType.INICIAR_COMPRA_TENDENCIA:
                return TrendPositionState.EN_POSICION
            else:
                return TrendPositionState.FUERA_DEL_MERCADO
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo estado de posición para {pair}: {e}")
            return TrendPositionState.FUERA_DEL_MERCADO
    
    def _detect_trend_signals(self, indicators: MarketIndicators) -> Dict[str, Any]:
        """
        Detecta señales específicas de tendencia.
        
        Args:
            indicators: Indicadores de mercado
            
        Returns:
            Diccionario con señales detectadas
        """
        signals = {
            'golden_cross': False,
            'death_cross': False,
            'trend_strength_ok': False,
            'sentiment_ok': False
        }
        
        try:
            # Detectar Cruce Dorado (SMA30 > SMA150)
            if indicators.sma30 and indicators.sma150:
                signals['golden_cross'] = indicators.sma30 > indicators.sma150
                
                # Para detectar cruce, necesitaríamos datos históricos
                # Por ahora solo verificamos la condición actual
                self.logger.info(f"📊 SMA30: {indicators.sma30:.2f}, SMA150: {indicators.sma150:.2f}")
                self.logger.info(f"📊 Cruce Dorado: {signals['golden_cross']}")
            
            # Detectar Cruce de la Muerte (SMA30 < SMA150)
            if indicators.sma30 and indicators.sma150:
                signals['death_cross'] = indicators.sma30 < indicators.sma150
                self.logger.info(f"📊 Cruce de la Muerte: {signals['death_cross']}")
            
            # Verificar fuerza de tendencia (ADX > 25)
            if indicators.adx:
                signals['trend_strength_ok'] = indicators.adx > 25
                self.logger.info(f"📊 ADX: {indicators.adx:.2f}, Fuerza OK: {signals['trend_strength_ok']}")
            
            # Verificar sentimiento favorable (> -0.1)
            if indicators.sentiment_7d_avg is not None:
                signals['sentiment_ok'] = indicators.sentiment_7d_avg > -0.1
                self.logger.info(f"📊 Sentimiento 7d: {indicators.sentiment_7d_avg:.3f}, OK: {signals['sentiment_ok']}")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error detectando señales de tendencia: {e}")
            return signals
    
    def _make_trend_decision(
        self,
        pair: str,
        current_state: TrendPositionState,
        indicators: MarketIndicators,
        thresholds: TradingThresholds,
        trend_signals: Dict[str, Any]
    ) -> TrendDecision:
        """
        Toma una decisión de tendencia basada en el estado actual y las señales.
        
        Args:
            pair: Par de trading
            current_state: Estado actual de posición
            indicators: Indicadores de mercado
            thresholds: Umbrales de decisión
            trend_signals: Señales de tendencia detectadas
            
        Returns:
            Decisión de tendencia
        """
        try:
            decision_type = DecisionType.MANTENER_ESPERA
            reason_parts = []
            
            # Lógica de decisión basada en el estado actual
            if current_state == TrendPositionState.FUERA_DEL_MERCADO:
                # Buscar señal de entrada
                if (trend_signals['golden_cross'] and 
                    trend_signals['trend_strength_ok'] and 
                    trend_signals['sentiment_ok']):
                    
                    decision_type = DecisionType.INICIAR_COMPRA_TENDENCIA
                    reason_parts.append("Cruce Dorado detectado")
                    reason_parts.append(f"ADX fuerte ({indicators.adx:.2f} > 25)")
                    reason_parts.append(f"Sentimiento favorable ({indicators.sentiment_7d_avg:.3f} > -0.1)")
                else:
                    decision_type = DecisionType.MANTENER_ESPERA
                    if not trend_signals['golden_cross']:
                        reason_parts.append("No hay Cruce Dorado")
                    if not trend_signals['trend_strength_ok']:
                        reason_parts.append(f"ADX débil ({indicators.adx:.2f} <= 25)")
                    if not trend_signals['sentiment_ok']:
                        reason_parts.append(f"Sentimiento desfavorable ({indicators.sentiment_7d_avg:.3f} <= -0.1)")
            
            elif current_state == TrendPositionState.EN_POSICION:
                # Buscar señal de salida
                if trend_signals['death_cross']:
                    decision_type = DecisionType.CERRAR_POSICION
                    reason_parts.append("Cruce de la Muerte detectado")
                else:
                    decision_type = DecisionType.MANTENER_POSICION
                    reason_parts.append("Tendencia alcista se mantiene")
            
            # Construir razón completa
            reason = f"Estado: {current_state.value}. {'; '.join(reason_parts)}"
            
            # Crear decisión
            decision = TrendDecision(
                pair=pair,
                decision=decision_type,
                reason=reason,
                indicators=indicators,
                thresholds=thresholds,
                timestamp=datetime.utcnow(),
                golden_cross=trend_signals['golden_cross'],
                death_cross=trend_signals['death_cross'],
                trend_strength_ok=trend_signals['trend_strength_ok'],
                sentiment_ok=trend_signals['sentiment_ok']
            )
            
            self.logger.info(f"🎯 Decisión TREND para {pair}: {decision_type.value}")
            self.logger.info(f"📝 Razón: {reason}")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error tomando decisión de tendencia: {e}")
            
            # Decisión de error
            return TrendDecision(
                pair=pair,
                decision=DecisionType.ERROR,
                reason=f"Error en análisis: {str(e)}",
                indicators=indicators,
                thresholds=thresholds,
                timestamp=datetime.utcnow(),
                success=False,
                error_message=str(e)
            ) 