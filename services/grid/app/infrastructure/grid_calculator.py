"""
Calculador de Grid Trading - Cálculos matemáticos de la grilla.
"""
from typing import List, Optional
from decimal import Decimal

from app.domain.interfaces import GridCalculator
from app.domain.entities import GridConfig, GridOrder
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GridTradingCalculator(GridCalculator):
    """Implementación simplificada del calculador de grid trading."""

    def __init__(self):
        """Inicializa el calculador."""
        logger.info("✅ GridTradingCalculator inicializado.")

    def calculate_order_amount(self, total_capital: float, grid_levels: int) -> Decimal:
        """Calcula la cantidad por orden basada en el capital total y niveles de grilla."""
        try:
            # Dividir el capital total entre el número de niveles
            capital_per_level = Decimal(total_capital) / Decimal(grid_levels)
            
            # Redondear a 6 decimales para evitar problemas de precisión
            amount = capital_per_level.quantize(Decimal('0.000001'))
            
            logger.debug(f"💰 Cantidad por nivel: {amount} (Capital total: ${total_capital:.2f}, Niveles: {grid_levels})")
            return amount
            
        except Exception as e:
            logger.error(f"❌ Error calculando cantidad de orden: {e}")
            return Decimal('0')

    def calculate_profit_per_trade(self, config: GridConfig, current_price: Decimal) -> Decimal:
        """Calcula la ganancia esperada por trade usando el spread y cantidad por nivel."""
        try:
            # Calcular el spread entre niveles
            spread_percent = Decimal(config.price_range_percent) / Decimal(config.grid_levels)
            spread_amount = current_price * (spread_percent / 100)
            
            # Calcular cantidad por nivel
            amount = self.calculate_order_amount(config.total_capital, config.grid_levels)
            
            # Ganancia por trade = spread * cantidad
            profit = spread_amount * amount
            
            logger.debug(f"💰 Ganancia esperada por trade: ${profit:.4f}")
            return profit
            
        except Exception as e:
            logger.error(f"❌ Error calculando ganancia por trade: {e}")
            return Decimal('0')

    def calculate_grid_levels(self, current_price: Decimal, config: GridConfig) -> List[Decimal]:
        """Calcula los niveles de precio para la grilla."""
        try:
            grid_levels = []
            
            # Calcular rango de precios
            price_range = current_price * (Decimal(config.price_range_percent) / 100)
            upper_bound = current_price + (price_range / 2)
            lower_bound = current_price - (price_range / 2)
            
            # Calcular step entre niveles
            total_range = upper_bound - lower_bound
            step = total_range / Decimal(config.grid_levels - 1)
            
            # Generar niveles de grilla
            for i in range(config.grid_levels):
                level_price = lower_bound + (step * Decimal(i))
                grid_levels.append(level_price)
            
            logger.debug(f"📊 Calculados {len(grid_levels)} niveles para {config.pair}")
            logger.debug(f"   Rango: ${lower_bound:.4f} - ${upper_bound:.4f}")
            
            return grid_levels
            
        except Exception as e:
            logger.error(f"❌ Error calculando niveles de grilla: {e}")
            return []

    def should_create_buy_order(self, current_price: Decimal, existing_orders: List[GridOrder], grid_levels: List[Decimal]) -> Optional[Decimal]:
        """Determina si se debe crear una orden de compra y a qué precio."""
        try:
            if not grid_levels:
                return None
            
            # Encontrar niveles por debajo del precio actual
            buy_levels = [level for level in grid_levels if level < current_price]
            
            if not buy_levels:
                return None
            
            # Obtener órdenes de compra existentes
            existing_buy_orders = [order for order in existing_orders if order.side == 'buy' and order.status == 'open']
            existing_buy_prices = {order.price for order in existing_buy_orders}
            
            # Encontrar el nivel más alto sin orden
            for buy_level in sorted(buy_levels, reverse=True):
                if buy_level not in existing_buy_prices:
                    logger.debug(f"📈 Sugerida orden de compra a ${buy_level:.4f}")
                    return buy_level
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error determinando orden de compra: {e}")
            return None

    def should_create_sell_order(self, current_price: Decimal, existing_orders: List[GridOrder], grid_levels: List[Decimal]) -> Optional[Decimal]:
        """Determina si se debe crear una orden de venta y a qué precio."""
        try:
            if not grid_levels:
                return None
            
            # Encontrar niveles por encima del precio actual
            sell_levels = [level for level in grid_levels if level > current_price]
            
            if not sell_levels:
                return None
            
            # Obtener órdenes de venta existentes
            existing_sell_orders = [order for order in existing_orders if order.side == 'sell' and order.status == 'open']
            existing_sell_prices = {order.price for order in existing_sell_orders}
            
            # Encontrar el nivel más bajo sin orden
            for sell_level in sorted(sell_levels):
                if sell_level not in existing_sell_prices:
                    logger.debug(f"📉 Sugerida orden de venta a ${sell_level:.4f}")
                    return sell_level
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error determinando orden de venta: {e}")
            return None

    def calculate_stop_loss_price(self, entry_price: Decimal, config: GridConfig, side: str) -> Optional[Decimal]:
        """Calcula el precio de stop loss."""
        try:
            if not config.enable_stop_loss:
                return None
            
            stop_loss_percent = Decimal(config.stop_loss_percent) / 100
            
            if side == 'buy':
                # Para órdenes de compra, stop loss por debajo del precio de entrada
                stop_loss_price = entry_price * (1 - stop_loss_percent)
            else:
                # Para órdenes de venta, stop loss por encima del precio de entrada
                stop_loss_price = entry_price * (1 + stop_loss_percent)
            
            logger.debug(f"🛡️ Stop loss para {side} a ${entry_price:.4f}: ${stop_loss_price:.4f}")
            return stop_loss_price
            
        except Exception as e:
            logger.error(f"❌ Error calculando stop loss: {e}")
            return None

    def is_price_in_grid_range(self, price: Decimal, grid_levels: List[Decimal]) -> bool:
        """Verifica si un precio está dentro del rango de la grilla."""
        try:
            if not grid_levels:
                return False
            
            min_level = min(grid_levels)
            max_level = max(grid_levels)
            
            return min_level <= price <= max_level
            
        except Exception as e:
            logger.error(f"❌ Error verificando rango de grilla: {e}")
            return False 