"""
Caso de Uso: Análisis Batch
===========================

Ejecuta análisis batch de todos los pares soportados.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.domain.interfaces import (
    MarketDataRepository, 
    DecisionRepository, 
    RecipeRepository,
    NotificationService
)
from app.domain.entities import TradingDecision, TrendDecision, BotType, DecisionType
from app.config import SUPPORTED_PAIRS

logger = logging.getLogger(__name__)


class BatchAnalysisUseCase:
    """
    Caso de uso para análisis batch de todos los pares.
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
    
    async def execute(self) -> Dict[str, Any]:
        """
        Ejecuta el análisis batch de todos los pares.
        
        Returns:
            Resultado del análisis batch
        """
        start_time = datetime.utcnow()
        self.logger.info("🚀 ========== INICIANDO ANÁLISIS BATCH ==========")
        self.logger.info(f"📊 Analizando {len(SUPPORTED_PAIRS)} pares: {', '.join(SUPPORTED_PAIRS)}")
        
        try:
            # Procesar cada par para ambas estrategias
            decisions: List[Any] = []  # Puede contener TradingDecision o TrendDecision
            successful_pairs = 0
            failed_pairs = 0
            
            for pair in SUPPORTED_PAIRS:
                try:
                    self.logger.info(f"📈 Analizando {pair}...")
                    
                    # ========== ANÁLISIS GRID ==========
                    grid_decision = await self._analyze_grid(pair)
                    if grid_decision:
                        decisions.append(grid_decision)
                        successful_pairs += 1
                    
                    # ========== ANÁLISIS TREND ==========
                    trend_decision = await self._analyze_trend(pair)
                    if trend_decision:
                        decisions.append(trend_decision)
                        successful_pairs += 1
                        
                except Exception as e:
                    self.logger.error(f"❌ Error analizando {pair}: {e}")
                    failed_pairs += 1
                    await self.notification_service.notify_error(
                        f"Error analizando {pair}", 
                        {"pair": pair, "error": str(e)}
                    )
            
            # El brain es estateless, no necesita notificar estado del servicio
            # Solo notifica cambios de decisiones individuales
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info("🎯 ========== ANÁLISIS BATCH COMPLETADO ==========")
            self.logger.info(f"✅ Pares exitosos: {successful_pairs}/{len(SUPPORTED_PAIRS)}")
            self.logger.info(f"❌ Pares fallidos: {failed_pairs}/{len(SUPPORTED_PAIRS)}")
            self.logger.info(f"⏱️ Duración: {duration:.2f}s")
            
            return {
                "status": "completed",
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "total_pairs": len(SUPPORTED_PAIRS),
                "successful_pairs": successful_pairs,
                "failed_pairs": failed_pairs,
                "decisions_made": len(decisions),
                "decisions": [decision.to_dict() for decision in decisions]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en análisis batch: {e}")
            await self.notification_service.notify_error(
                "Error en análisis batch", 
                {"error": str(e), "timestamp": start_time.isoformat()}
            )
            
            return {
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e),
                "total_pairs": len(SUPPORTED_PAIRS),
                "successful_pairs": 0,
                "failed_pairs": len(SUPPORTED_PAIRS),
                "decisions_made": 0
            }
    
    def _make_decision(
        self, 
        pair: str, 
        indicators, 
        thresholds
    ) -> TradingDecision:
        """
        Toma una decisión basada en indicadores y umbrales.
        
        Args:
            pair: Par de trading
            indicators: Indicadores de mercado
            thresholds: Umbrales de decisión
            
        Returns:
            Decisión de trading
        """
        try:
            # Evaluar condiciones
            adx_ok = indicators.adx is None or indicators.adx < thresholds.adx_threshold
            volatility_ok = indicators.volatility is None or indicators.volatility > thresholds.volatility_threshold
            sentiment_ok = indicators.sentiment is None or indicators.sentiment > thresholds.sentiment_threshold
            
            # Construir razón detallada
            detalles = []
            detalles.append(f"ADX={indicators.adx:.2f} < {thresholds.adx_threshold}" if adx_ok else f"ADX={indicators.adx:.2f} >= {thresholds.adx_threshold}")
            detalles.append(f"Volatilidad={indicators.volatility:.4f} > {thresholds.volatility_threshold:.4f}" if volatility_ok else f"Volatilidad={indicators.volatility:.4f} <= {thresholds.volatility_threshold:.4f}")
            if indicators.sentiment is not None:
                detalles.append(f"Sentimiento={indicators.sentiment:.3f} > {thresholds.sentiment_threshold:.3f}" if sentiment_ok else f"Sentimiento={indicators.sentiment:.3f} <= {thresholds.sentiment_threshold:.3f}")
            else:
                detalles.append("Sentimiento=N/A (no disponible)")
            
            # Tomar decisión
            if adx_ok and volatility_ok and sentiment_ok:
                decision_type = DecisionType.OPERATE
                reason = f"Condiciones favorables: {'; '.join(detalles)}"
            else:
                decision_type = DecisionType.PAUSE
                reason = f"Condiciones desfavorables: {'; '.join(detalles)}"
            
            # Crear decisión
            decision = TradingDecision(
                pair=pair,
                decision=decision_type,
                reason=reason,
                indicators=indicators,
                thresholds=thresholds,
                bot_type=BotType.GRID,
                timestamp=datetime.utcnow(),
                success=True
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"❌ Error tomando decisión para {pair}: {e}")
            
            # Decisión de error
            from app.domain.entities import MarketIndicators, TradingThresholds
            error_indicators = MarketIndicators()
            error_thresholds = TradingThresholds(
                adx_threshold=0.0,
                volatility_threshold=0.0,
                sentiment_threshold=0.0,
                bot_type=BotType.GRID
            )
            
            return TradingDecision(
                pair=pair,
                decision=DecisionType.ERROR,
                reason=f"Error en análisis: {str(e)}",
                indicators=error_indicators,
                thresholds=error_thresholds,
                bot_type=BotType.GRID,
                timestamp=datetime.utcnow(),
                success=False,
                error_message=str(e)
            )
    
    async def _analyze_grid(self, pair: str) -> Optional[TradingDecision]:
        """
        Analiza un par para la estrategia GRID.
        
        Args:
            pair: Par de trading
            
        Returns:
            Decisión de GRID o None si hay error
        """
        try:
            # Obtener datos de mercado
            market_data = await self.market_data_repo.fetch_market_data(pair)
            if not market_data:
                self.logger.warning(f"⚠️ No se pudieron obtener datos para {pair} (GRID)")
                return None
            
            # Calcular indicadores
            indicators = await self.market_data_repo.calculate_indicators(market_data)
            if not indicators:
                self.logger.warning(f"⚠️ No se pudieron calcular indicadores para {pair} (GRID)")
                return None
            
            # Obtener receta
            recipe = await self.recipe_repo.get_recipe(pair, BotType.GRID)
            if not recipe:
                self.logger.warning(f"⚠️ No se encontró receta GRID para {pair}")
                return None
            
            # Obtener umbrales de la receta
            thresholds = recipe.get_thresholds()
            
            # Tomar decisión basada en indicadores y umbrales
            decision = self._make_decision(pair, indicators, thresholds)
            
            # Guardar decisión
            saved = await self.decision_repo.save_decision(decision)
            if saved:
                # Notificar cambio de decisión
                await self.notification_service.notify_decision_change(decision)
                
                self.logger.info(f"✅ {pair} GRID: {decision.decision.value} - {decision.reason}")
                return decision
            else:
                self.logger.error(f"❌ Error guardando decisión GRID para {pair}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error analizando GRID para {pair}: {e}")
            return None
    
    async def _analyze_trend(self, pair: str) -> Optional[TrendDecision]:
        """
        Analiza un par para la estrategia TREND.
        
        Args:
            pair: Par de trading
            
        Returns:
            Decisión de TREND o None si hay error
        """
        try:
            # Obtener datos de mercado (timeframe 1d para tendencia)
            market_data = await self.market_data_repo.fetch_market_data(pair, timeframe='1d', days=200)
            if not market_data:
                self.logger.warning(f"⚠️ No se pudieron obtener datos para {pair} (TREND)")
                return None
            
            # Calcular indicadores
            indicators = await self.market_data_repo.calculate_indicators(market_data)
            if not indicators:
                self.logger.warning(f"⚠️ No se pudieron calcular indicadores para {pair} (TREND)")
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
            return None
    
    async def _get_current_position_state(self, pair: str):
        """
        Obtiene el estado actual de posición para el par.
        Por defecto asume FUERA_DEL_MERCADO.
        
        Args:
            pair: Par de trading
            
        Returns:
            Estado actual de posición
        """
        try:
            from app.domain.entities import TrendPositionState
            
            # Buscar la última decisión para ver si hay una posición activa
            last_decision = await self.decision_repo.get_latest_decision(pair, BotType.TREND)
            
            if last_decision and last_decision.decision == DecisionType.INICIAR_COMPRA_TENDENCIA:
                return TrendPositionState.EN_POSICION
            else:
                return TrendPositionState.FUERA_DEL_MERCADO
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo estado de posición para {pair}: {e}")
            from app.domain.entities import TrendPositionState
            return TrendPositionState.FUERA_DEL_MERCADO
    
    def _detect_trend_signals(self, indicators):
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
        current_state,
        indicators,
        thresholds,
        trend_signals
    ):
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
            from app.domain.entities import TrendPositionState, TrendDecision
            
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
            from app.domain.entities import TrendDecision, TrendPositionState
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