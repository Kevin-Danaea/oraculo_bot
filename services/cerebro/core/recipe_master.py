"""
Recetas Maestras del Cerebro - Condiciones específicas por par
Define las condiciones optimizadas para cada par según backtesting y análisis.
"""

from typing import Dict, Any, Optional
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class RecipeMaster:
    """
    Maneja las recetas maestras para cada par de trading.
    Cada par tiene condiciones específicas optimizadas por backtesting.
    """
    
    @staticmethod
    def get_recipe_for_pair(pair: str) -> Dict[str, Any]:
        """
        Obtiene la receta maestra para un par específico
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT', 'BTC/USDT', 'POL/USDT')
            
        Returns:
            Diccionario con la receta maestra del par
        """
        recipes = {
            'ETH/USDT': {
                'name': 'Receta Maestra ETH',
                'conditions': {
                    'adx_threshold': 30,  # ADX debe ser menor a 30
                    'bollinger_bandwidth_threshold': 0.025,  # Ancho de banda > 0.025
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                'grid_config': {
                    'price_range_percent': 10.0,
                    'grid_levels': 30
                },
                'description': 'Condiciones optimizadas para ETH/USDT basadas en backtesting'
            },
            'BTC/USDT': {
                'name': 'Receta Maestra BTC',
                'conditions': {
                    'adx_threshold': 25,  # ADX debe ser menor a 25
                    'bollinger_bandwidth_threshold': 0.035,  # Ancho de banda > 0.035
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                'grid_config': {
                    'price_range_percent': 7.5,  # RECETA MAESTRA BTC
                    'grid_levels': 30
                },
                'description': 'Condiciones optimizadas para BTC/USDT basadas en backtesting'
            },
            'AVAX/USDT': {
                'name': 'Receta Maestra AVAX',
                'conditions': {
                    'adx_threshold': 35,  # ADX debe ser menor a 35
                    'bollinger_bandwidth_threshold': 0.020,  # Ancho de banda > 0.020
                    'sentiment_threshold': -0.20,  # Sentimiento > -0.20
                },
                'grid_config': {
                    'price_range_percent': 10.0,  # RECETA MAESTRA AVAX
                    'grid_levels': 30
                },
                'description': 'Condiciones optimizadas para AVAX/USDT basadas en backtesting'
            }
        }
        
        return recipes.get(pair, recipes['ETH/USDT'])  # Fallback a ETH si no existe
    
    @staticmethod
    def evaluate_conditions(pair: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa si se cumplen las condiciones de la receta maestra para un par
        
        Args:
            pair: Par de trading
            market_data: Datos del mercado (ADX, Bollinger, Sentimiento)
            
        Returns:
            Diccionario con resultado de la evaluación
        """
        try:
            recipe = RecipeMaster.get_recipe_for_pair(pair)
            conditions = recipe['conditions']
            
            # Extraer datos del mercado
            adx = market_data.get('adx', 0)
            bollinger_bandwidth = market_data.get('bollinger_bandwidth', 0)
            sentiment = market_data.get('sentiment', 0)
            
            # Evaluar condiciones
            adx_ok = adx < conditions['adx_threshold']
            bollinger_ok = bollinger_bandwidth > conditions['bollinger_bandwidth_threshold']
            sentiment_ok = sentiment > conditions['sentiment_threshold']
            
            # Todas las condiciones deben cumplirse
            all_conditions_met = adx_ok and bollinger_ok and sentiment_ok
            
            result = {
                'pair': pair,
                'recipe_name': recipe['name'],
                'can_operate': all_conditions_met,
                'conditions': {
                    'adx': {
                        'value': adx,
                        'threshold': conditions['adx_threshold'],
                        'met': adx_ok,
                        'description': f"ADX < {conditions['adx_threshold']}"
                    },
                    'bollinger_bandwidth': {
                        'value': bollinger_bandwidth,
                        'threshold': conditions['bollinger_bandwidth_threshold'],
                        'met': bollinger_ok,
                        'description': f"Bollinger Bandwidth > {conditions['bollinger_bandwidth_threshold']}"
                    },
                    'sentiment': {
                        'value': sentiment,
                        'threshold': conditions['sentiment_threshold'],
                        'met': sentiment_ok,
                        'description': f"Sentiment > {conditions['sentiment_threshold']}"
                    }
                },
                'grid_config': recipe['grid_config'],
                'reason': RecipeMaster._generate_reason(all_conditions_met, adx_ok, bollinger_ok, sentiment_ok, recipe)
            }
            
            logger.info(f"🧠 Evaluación {pair}: {'✅ OPERAR' if all_conditions_met else '❌ PAUSAR'}")
            logger.info(f"   ADX: {adx:.2f} < {conditions['adx_threshold']} = {adx_ok}")
            logger.info(f"   Bollinger: {bollinger_bandwidth:.4f} > {conditions['bollinger_bandwidth_threshold']} = {bollinger_ok}")
            logger.info(f"   Sentiment: {sentiment:.3f} > {conditions['sentiment_threshold']} = {sentiment_ok}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error evaluando condiciones para {pair}: {e}")
            return {
                'pair': pair,
                'can_operate': False,
                'error': str(e),
                'reason': f"Error evaluando condiciones: {e}"
            }
    
    @staticmethod
    def _generate_reason(can_operate: bool, adx_ok: bool, bollinger_ok: bool, 
                        sentiment_ok: bool, recipe: Dict[str, Any]) -> str:
        """Genera la razón de la decisión"""
        if can_operate:
            return f"✅ Todas las condiciones de {recipe['name']} se cumplen"
        
        failed_conditions = []
        if not adx_ok:
            failed_conditions.append("ADX muy alto")
        if not bollinger_ok:
            failed_conditions.append("Volatilidad insuficiente")
        if not sentiment_ok:
            failed_conditions.append("Sentimiento negativo")
        
        return f"❌ Condiciones no cumplidas: {', '.join(failed_conditions)}"
    
    @staticmethod
    def get_all_supported_pairs() -> list:
        """Retorna todos los pares soportados con recetas maestras"""
        return ['ETH/USDT', 'BTC/USDT', 'AVAX/USDT']
    
    @staticmethod
    def get_recipe_summary() -> Dict[str, Any]:
        """Retorna un resumen de todas las recetas maestras"""
        pairs = RecipeMaster.get_all_supported_pairs()
        summary = {}
        
        for pair in pairs:
            recipe = RecipeMaster.get_recipe_for_pair(pair)
            summary[pair] = {
                'name': recipe['name'],
                'conditions': recipe['conditions'],
                'grid_config': recipe['grid_config'],
                'description': recipe['description']
            }
        
        return summary


# Función de conveniencia para uso directo
def evaluate_pair_conditions(pair: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de conveniencia para evaluar condiciones de un par
    
    Args:
        pair: Par de trading
        market_data: Datos del mercado
        
    Returns:
        Resultado de la evaluación
    """
    return RecipeMaster.evaluate_conditions(pair, market_data)


def get_recipe_for_pair(pair: str) -> Dict[str, Any]:
    """
    Función de conveniencia para obtener receta de un par
    
    Args:
        pair: Par de trading
        
    Returns:
        Receta maestra del par
    """
    return RecipeMaster.get_recipe_for_pair(pair)


__all__ = [
    'RecipeMaster',
    'evaluate_pair_conditions',
    'get_recipe_for_pair'
] 