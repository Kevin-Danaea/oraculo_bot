"""
Repositorio de Recetas
======================

Implementación concreta del repositorio de recetas de trading.
"""

import logging
from typing import Dict, Any, Optional, List

from app.domain.interfaces import RecipeRepository
from app.domain.entities import TradingRecipe, BotType

logger = logging.getLogger(__name__)


class InMemoryRecipeRepository(RecipeRepository):
    """
    Implementación en memoria del repositorio de recetas.
    En el futuro, esto podría ser reemplazado por una base de datos.
    """
    
    def __init__(self):
        """Inicializa el repositorio con las recetas maestras."""
        self.logger = logging.getLogger(__name__)
        self._recipes = self._load_master_recipes()
    
    def _load_master_recipes(self) -> Dict[str, TradingRecipe]:
        """
        Carga las recetas maestras desde la configuración.
        Returns:
            Diccionario de recetas por par y tipo de bot
        """
        recipes = {}
        # Recetas para GRID
        grid_recipes = {
            'ETH/USDT_GRID': TradingRecipe(
                pair='ETH/USDT',
                name='Receta Maestra ETH',
                conditions={
                    'adx_threshold': 30,  # ADX debe ser menor a 30
                    'bollinger_bandwidth_threshold': 0.025,  # Ancho de banda > 0.025
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                grid_config={
                    'price_range_percent': 10.0,
                    'grid_levels': 30
                },
                description='Condiciones optimizadas para ETH/USDT basadas en backtesting',
                bot_type=BotType.GRID
            ),
            'BTC/USDT_GRID': TradingRecipe(
                pair='BTC/USDT',
                name='Receta Maestra BTC',
                conditions={
                    'adx_threshold': 25,  # ADX debe ser menor a 25
                    'bollinger_bandwidth_threshold': 0.035,  # Ancho de banda > 0.035
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                grid_config={
                    'price_range_percent': 7.5,  # RECETA MAESTRA BTC
                    'grid_levels': 30
                },
                description='Condiciones optimizadas para BTC/USDT basadas en backtesting',
                bot_type=BotType.GRID
            ),
            'AVAX/USDT_GRID': TradingRecipe(
                pair='AVAX/USDT',
                name='Receta Maestra AVAX',
                conditions={
                    'adx_threshold': 35,  # ADX debe ser menor a 35
                    'bollinger_bandwidth_threshold': 0.020,  # Ancho de banda > 0.020
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                grid_config={
                    'price_range_percent': 10.0,  # RECETA MAESTRA AVAX
                    'grid_levels': 30
                },
                description='Condiciones optimizadas para AVAX/USDT basadas en backtesting',
                bot_type=BotType.GRID
            )
        }
        # Recetas para TREND (solo ETH/USDT por ahora)
        trend_recipes = {
            'ETH/USDT_TREND': TradingRecipe(
                pair='ETH/USDT',
                name='Receta TREND Maestra ETH',
                conditions={
                    'adx_threshold': 30,
                    'bollinger_bandwidth_threshold': 0.025,
                    'sentiment_threshold': -0.20,
                    'adx_trend_threshold': 25.0,
                    'sentiment_trend_threshold': -0.1,
                },
                grid_config={
                    'sma_short_period': 30,
                    'sma_long_period': 150,
                    'adx_period': 14,
                    'sentiment_avg_days': 7,
                },
                description='Receta optimizada para estrategia TREND en ETH/USDT',
                bot_type=BotType.TREND
            )
        }
        recipes.update(grid_recipes)
        recipes.update(trend_recipes)
        self.logger.info(f"✅ Cargadas {len(recipes)} recetas maestras (GRID: {len(grid_recipes)}, TREND: {len(trend_recipes)})")
        return recipes
    
    async def get_recipe(self, pair: str, bot_type: BotType) -> Optional[TradingRecipe]:
        """
        Obtiene la receta para un par y tipo de bot específico.
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
        Returns:
            Receta o None si no existe
        """
        try:
            recipe_key = f"{pair}_{bot_type.value}"
            recipe = self._recipes.get(recipe_key)
            if recipe:
                self.logger.debug(f"✅ Receta encontrada para {pair} ({bot_type.value})")
                return recipe
            self.logger.warning(f"⚠️ No se encontró receta para {pair} ({bot_type.value})")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo receta para {pair}: {e}")
            return None

    async def get_all_recipes(self) -> List[TradingRecipe]:
        """
        Obtiene todas las recetas disponibles.
        Returns:
            Lista de todas las recetas
        """
        try:
            recipes = list(self._recipes.values())
            self.logger.debug(f"✅ Obtenidas {len(recipes)} recetas")
            return recipes
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo todas las recetas: {e}")
            return []

    async def get_supported_pairs(self, bot_type: Optional[BotType] = None) -> List[str]:
        """
        Obtiene todos los pares soportados, opcionalmente filtrando por tipo de bot.
        Args:
            bot_type: Si se especifica, solo retorna los pares para ese tipo de bot
        Returns:
            Lista de pares
        """
        try:
            if bot_type is not None:
                return [r.pair for k, r in self._recipes.items() if k.endswith(f"_{bot_type.value}")]
            return [r.pair for r in self._recipes.values()]
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo pares soportados: {e}")
            return []
    
    async def add_recipe(self, recipe: TradingRecipe) -> bool:
        """
        Agrega una nueva receta (método adicional para futuras expansiones).
        
        Args:
            recipe: Receta a agregar
            
        Returns:
            True si se agregó correctamente
        """
        try:
            self._recipes[recipe.pair] = recipe
            self.logger.info(f"✅ Receta agregada para {recipe.pair}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error agregando receta para {recipe.pair}: {e}")
            return False
    
    async def update_recipe(self, pair: str, bot_type: BotType, updated_recipe: TradingRecipe) -> bool:
        """
        Actualiza una receta existente.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            updated_recipe: Receta actualizada
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            if pair in self._recipes and self._recipes[pair].bot_type == bot_type:
                self._recipes[pair] = updated_recipe
                self.logger.info(f"✅ Receta actualizada para {pair}")
                return True
            else:
                self.logger.warning(f"⚠️ No se encontró receta para actualizar: {pair}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando receta para {pair}: {e}")
            return False
    
    async def delete_recipe(self, pair: str, bot_type: BotType) -> bool:
        """
        Elimina una receta.
        
        Args:
            pair: Par de trading
            bot_type: Tipo de bot
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            if pair in self._recipes and self._recipes[pair].bot_type == bot_type:
                del self._recipes[pair]
                self.logger.info(f"✅ Receta eliminada para {pair}")
                return True
            else:
                self.logger.warning(f"⚠️ No se encontró receta para eliminar: {pair}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error eliminando receta para {pair}: {e}")
            return False
    
    def get_recipe_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de todas las recetas.
        
        Returns:
            Resumen de recetas
        """
        try:
            summary = {}
            for pair, recipe in self._recipes.items():
                summary[pair] = {
                    'name': recipe.name,
                    'conditions': recipe.conditions,
                    'grid_config': recipe.grid_config,
                    'description': recipe.description,
                    'bot_type': recipe.bot_type.value
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo resumen de recetas: {e}")
            return {} 