"""
Caso de Uso: Analizar Par Específico
====================================

Analiza un par de trading específico y toma una decisión de trading.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.domain.entities import (
    TradingDecision, 
    DecisionType,
    MarketIndicators, 
    TradingRecipe, 
    BotType,
    TradingThresholds
)
from app.domain.interfaces import (
    MarketDataRepository,
    DecisionRepository,
    RecipeRepository
)

logger = logging.getLogger(__name__)


class AnalyzePairUseCase:
    """
    Caso de uso para analizar un par específico y tomar una decisión de trading.
    """
    
    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        decision_repo: DecisionRepository,
        recipe_repo: RecipeRepository
    ):
        """
        Inicializa el caso de uso.
        
        Args:
            market_data_repo: Repositorio de datos de mercado
            decision_repo: Repositorio de decisiones
            recipe_repo: Repositorio de recetas
        """
        self.market_data_repo = market_data_repo
        self.decision_repo = decision_repo
        self.recipe_repo = recipe_repo
    
    async def execute(
        self, 
        pair: str, 
        bot_type: BotType = BotType.GRID,
        timeframe: str = '4h',
        days: int = 40
    ) -> TradingDecision:
        """
        Ejecuta el análisis de un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            bot_type: Tipo de bot para el cual tomar la decisión
            timeframe: Marco temporal para los datos
            days: Número de días de historial
            
        Returns:
            Decisión de trading
        """
        try:
            logger.info(f"🔍 Analizando {pair} para {bot_type.value}...")
            
            # 1. Obtener la receta para el par y tipo de bot
            recipe = await self.recipe_repo.get_recipe(pair, bot_type)
            if not recipe:
                raise ValueError(f"No se encontró receta para {pair} y {bot_type.value}")
            
            # 2. Obtener datos de mercado
            market_data = await self.market_data_repo.fetch_market_data(pair, timeframe, days)
            if not market_data:
                raise Exception(f"No se pudieron obtener datos para {pair}")
            
            # 3. Calcular indicadores
            indicators = await self.market_data_repo.calculate_indicators(market_data)
            if not indicators:
                raise Exception(f"No se pudieron calcular indicadores para {pair}")
            
            # 4. Tomar decisión
            decision_type = self._make_decision(indicators, recipe)
            
            # 5. Generar razón
            reason = self._generate_reason(decision_type, indicators, recipe)
            
            # 6. Crear objeto de decisión
            trading_decision = TradingDecision(
                pair=pair,
                decision=decision_type,
                reason=reason,
                indicators=indicators,
                thresholds=recipe.get_thresholds(),
                bot_type=bot_type,
                timestamp=datetime.utcnow(),
                success=True
            )
            
            # 7. Guardar decisión
            await self.decision_repo.save_decision(trading_decision)
            
            logger.info(f"✅ Decisión para {pair}: {decision_type.value}")
            logger.info(f"📝 Razón: {reason}")
            
            return trading_decision
            
        except Exception as e:
            logger.error(f"❌ Error analizando {pair}: {str(e)}")
            
            # Crear decisión de error
            error_decision = TradingDecision(
                pair=pair,
                decision=DecisionType.ERROR,
                reason=f"Error en análisis: {str(e)}",
                indicators=MarketIndicators(adx=0, volatility=0, sentiment=None),
                thresholds=TradingThresholds(
                    adx_threshold=0,
                    volatility_threshold=0,
                    sentiment_threshold=0,
                    bot_type=bot_type
                ),
                bot_type=bot_type,
                timestamp=datetime.utcnow(),
                success=False,
                error_message=str(e)
            )
            
            # Intentar guardar la decisión de error
            try:
                await self.decision_repo.save_decision(error_decision)
            except Exception as save_error:
                logger.error(f"❌ Error guardando decisión de error: {save_error}")
            
            return error_decision
    
    def _make_decision(
        self, 
        indicators: MarketIndicators, 
        recipe: TradingRecipe
    ) -> DecisionType:
        """
        Toma una decisión basada en los indicadores y la receta.
        
        Args:
            indicators: Indicadores de mercado
            recipe: Receta de trading
            
        Returns:
            Decisión de trading
        """
        thresholds = recipe.get_thresholds()
        
        # Validar indicadores críticos
        if indicators.adx is None or indicators.volatility is None:
            return DecisionType.ERROR
        
        # Evaluar condiciones
        adx_condition = indicators.adx < thresholds.adx_threshold
        volatility_condition = indicators.volatility > thresholds.volatility_threshold
        
        # Manejar sentimiento (puede ser None)
        if indicators.sentiment is not None:
            sentiment_condition = indicators.sentiment > thresholds.sentiment_threshold
        else:
            sentiment_condition = True  # Si no hay datos de sentimiento, usar valor por defecto
            logger.warning("⚠️ No hay datos de sentimiento disponibles, usando valor por defecto")
        
        # Todas las condiciones deben cumplirse
        if adx_condition and volatility_condition and sentiment_condition:
            return DecisionType.OPERATE
        else:
            return DecisionType.PAUSE
    
    def _generate_reason(
        self, 
        decision: DecisionType, 
        indicators: MarketIndicators, 
        recipe: TradingRecipe
    ) -> str:
        """
        Genera una razón para la decisión tomada.
        """
        thresholds = recipe.get_thresholds()
        detalles = []
        if indicators.adx is not None:
            detalles.append(f"ADX={indicators.adx:.2f} < {thresholds.adx_threshold}" if indicators.adx < thresholds.adx_threshold else f"ADX={indicators.adx:.2f} >= {thresholds.adx_threshold}")
        if indicators.volatility is not None:
            detalles.append(f"Volatilidad={indicators.volatility:.4f} > {thresholds.volatility_threshold:.4f}" if indicators.volatility > thresholds.volatility_threshold else f"Volatilidad={indicators.volatility:.4f} <= {thresholds.volatility_threshold:.4f}")
        if indicators.sentiment is not None:
            detalles.append(f"Sentimiento={indicators.sentiment:.3f} > {thresholds.sentiment_threshold:.3f}" if indicators.sentiment > thresholds.sentiment_threshold else f"Sentimiento={indicators.sentiment:.3f} <= {thresholds.sentiment_threshold:.3f}")
        else:
            detalles.append("Sentimiento=N/A (no disponible)")
        if decision == DecisionType.ERROR:
            return f"Error en análisis: indicadores críticos faltantes"
        if decision == DecisionType.OPERATE:
            return f"✅ Todas las condiciones de {recipe.name} se cumplen: {'; '.join(detalles)}"
        # Si es PAUSE, identificar qué condiciones no se cumplieron
        return f"❌ Condiciones no cumplidas: {'; '.join(detalles)}" 