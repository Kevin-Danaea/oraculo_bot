"""
Estrategia de Grid Trading - Cálculos y lógica de grilla.
Maneja cálculos de precios, cantidades, distribución y profit dinámico.
"""

from typing import Dict, Any
from decimal import Decimal, ROUND_DOWN
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


def calculate_dynamic_profit_percentage(config: Dict[str, Any]) -> float:
    """
    Calcula el porcentaje de ganancia de forma dinámica basado en la estrategia
    
    Args:
        config: Configuración del bot
        
    Returns:
        Porcentaje de ganancia como decimal (ej: 0.01 para 1%)
    """
    try:
        price_range_percent = config['price_range_percent']
        grid_levels = config['grid_levels']
        
        # Calcular profit dinámico: rango de precio dividido entre niveles
        # Esto asegura que cada nivel tenga una ganancia proporcional al rango
        dynamic_profit = (price_range_percent / 100) / grid_levels
        
        # Aplicar un factor de seguridad para garantizar ganancias
        # Mínimo 0.5% para cubrir fees, máximo 5% para no ser demasiado agresivo
        min_profit = 0.005  # 0.5%
        max_profit = 0.05   # 5%
        
        profit_percentage = max(min_profit, min(dynamic_profit, max_profit))
        
        logger.info(f"💹 Profit dinámico calculado: {profit_percentage:.3f} ({profit_percentage*100:.2f}%)")
        logger.info(f"📊 Basado en: rango {price_range_percent}% / {grid_levels} niveles")
        
        return profit_percentage
        
    except Exception as e:
        logger.error(f"❌ Error calculando profit dinámico: {e}")
        # Fallback a 1% si hay error
        return 0.01


def calculate_grid_prices(current_price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula los precios de compra y venta para la grilla
    
    Args:
        current_price: Precio actual del activo
        config: Configuración validada del bot
        
    Returns:
        Dict con listas de precios de compra y venta
    """
    try:
        grid_levels = config['grid_levels']
        price_range_percent = config['price_range_percent']
        
        # Calcular rango de precios
        price_range = current_price * (price_range_percent / 100)
        min_price = current_price - (price_range / 2)
        max_price = current_price + (price_range / 2)
        
        # Dividir niveles entre compras y ventas
        buy_levels = grid_levels // 2
        sell_levels = grid_levels - buy_levels
        
        # Calcular precios de compra (por debajo del precio actual)
        buy_prices = []
        if buy_levels > 0:
            price_step = (current_price - min_price) / buy_levels
            for i in range(buy_levels):
                buy_price = current_price - price_step * (i + 1)
                buy_prices.append(round(buy_price, 2))
        
        # Calcular precios de venta iniciales (solo si tenemos balance del activo)
        sell_prices = []
        if sell_levels > 0:
            price_step = (max_price - current_price) / sell_levels
            for i in range(sell_levels):
                sell_price = current_price + price_step * (i + 1)
                sell_prices.append(round(sell_price, 2))
        
        logger.info(f"📊 Rango: ${min_price:.2f} - ${max_price:.2f}")
        logger.info(f"🟢 Precios compra: {buy_prices}")
        logger.info(f"🔴 Precios venta iniciales: {sell_prices}")
        
        return {
            'buy_prices': buy_prices,
            'sell_prices': sell_prices,
            'min_price': min_price,
            'max_price': max_price,
            'price_range': price_range
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculando precios de grilla: {e}")
        raise


def calculate_order_quantity(capital_per_order: float, price: float, min_qty: float = 0.001) -> float:
    """
    Calcula la cantidad de la orden basada en el capital disponible
    
    Args:
        capital_per_order: Capital disponible para esta orden
        price: Precio de la orden
        min_qty: Cantidad mínima permitida
        
    Returns:
        Cantidad calculada para la orden
    """
    try:
        # Calcular cantidad cruda
        raw_quantity = capital_per_order / price
        
        # Redondear hacia abajo para evitar errores de balance insuficiente
        quantity = float(Decimal(str(raw_quantity)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        
        # Verificar cantidad mínima
        if quantity < min_qty:
            logger.warning(f"⚠️ Cantidad calculada ({quantity}) menor que mínimo ({min_qty})")
            quantity = min_qty
        
        return quantity
        
    except Exception as e:
        logger.error(f"❌ Error calculando cantidad: {e}")
        raise


__all__ = [
    'calculate_dynamic_profit_percentage',
    'calculate_grid_prices',
    'calculate_order_quantity'
] 