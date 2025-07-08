"""
Caso de Uso: Análisis Batch
===========================

Ejecuta análisis batch de todos los pares soportados.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from app.domain.interfaces import (
    MarketDataRepository, 
    DecisionRepository, 
    RecipeRepository,
    NotificationService
)
from app.domain.entities import TradingDecision, BotType
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
            # Procesar cada par
            decisions: List[TradingDecision] = []
            successful_pairs = 0
            failed_pairs = 0
            
            for pair in SUPPORTED_PAIRS:
                try:
                    self.logger.info(f"📈 Analizando {pair}...")
                    
                    # Obtener datos de mercado
                    market_data = await self.market_data_repo.fetch_market_data(pair)
                    if not market_data:
                        self.logger.warning(f"⚠️ No se pudieron obtener datos para {pair}")
                        failed_pairs += 1
                        continue
                    
                    # Calcular indicadores
                    indicators = await self.market_data_repo.calculate_indicators(market_data)
                    if not indicators:
                        self.logger.warning(f"⚠️ No se pudieron calcular indicadores para {pair}")
                        failed_pairs += 1
                        continue
                    
                    # Obtener receta
                    recipe = await self.recipe_repo.get_recipe(pair, BotType.GRID)
                    if not recipe:
                        self.logger.warning(f"⚠️ No se encontró receta para {pair}")
                        failed_pairs += 1
                        continue
                    
                    # Obtener umbrales de la receta
                    thresholds = recipe.get_thresholds()
                    
                    # Tomar decisión basada en indicadores y umbrales
                    decision = self._make_decision(pair, indicators, thresholds)
                    
                    # Guardar decisión
                    saved = await self.decision_repo.save_decision(decision)
                    if saved:
                        decisions.append(decision)
                        successful_pairs += 1
                        
                        # Notificar cambio de decisión
                        await self.notification_service.notify_decision_change(decision)
                        
                        self.logger.info(f"✅ {pair}: {decision.decision.value} - {decision.reason}")
                    else:
                        self.logger.error(f"❌ Error guardando decisión para {pair}")
                        failed_pairs += 1
                        
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
                decision_type = "OPERAR_GRID"
                reason = f"Condiciones favorables: {'; '.join(detalles)}"
            else:
                decision_type = "PAUSAR_GRID"
                reason = f"Condiciones desfavorables: {'; '.join(detalles)}"
            
            # Crear decisión
            from app.domain.entities import DecisionType
            decision = TradingDecision(
                pair=pair,
                decision=DecisionType(decision_type),
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
            from app.domain.entities import DecisionType, MarketIndicators, TradingThresholds
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