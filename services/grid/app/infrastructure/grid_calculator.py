"""
Calculador de Grid Trading - Cálculos matemáticos de la grilla.
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.domain.interfaces import GridCalculator
from app.domain.entities import GridConfig, GridOrder
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GridTradingCalculator(GridCalculator):
    """Implementación simplificada del calculador de grid trading."""

    def __init__(self):
        """Inicializa el calculador."""
        logger.info("✅ GridTradingCalculator inicializado.")

    def calculate_order_amount(self, total_capital: float, grid_levels: int, current_price: Decimal | None = None) -> Decimal:
        """Calcula la cantidad por orden asegurando no superar el capital total.

        Distribuye el capital total entre todos los niveles de la grilla para maximizar
        el uso del capital asignado. Si `current_price` se proporciona, valida que el
        valor de la orden sea al menos 10 USDT; de lo contrario ajusta la cantidad.
        """
        try:
            # Evitar división entre cero
            if grid_levels <= 0:
                raise ValueError("grid_levels debe ser > 0")

            # Distribuir capital entre todos los niveles de la grilla
            # NOTA: Usamos grid_levels completo, no grid_levels // 2
            capital_per_order = Decimal(total_capital) / Decimal(grid_levels)

            # Si se proporciona current_price, asegurar mínimo 10 USDT
            if current_price:
                min_amount = Decimal('10') / current_price
                amount = max(min_amount, capital_per_order / current_price)
            else:
                amount = capital_per_order

            # Redondear a 6 decimales
            amount = amount.quantize(Decimal('0.000001'))

            logger.debug(
                f"💰 Cantidad por orden: {amount} (Capital total: ${total_capital:.2f}, "
                f"Niveles totales: {grid_levels}, Capital por nivel: ${capital_per_order:.2f})"
            )
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
            
            # Calcular cantidad por nivel usando la nueva lógica
            # Usar la mitad del capital total para las órdenes de compra
            half_capital = config.total_capital / 2
            amount = self.calculate_order_amount(half_capital, config.grid_levels, current_price)
            
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
            
            # Contar órdenes activas totales (buy + sell)
            active_orders_total = len([o for o in existing_orders if o.status == 'open'])
            max_active_orders = max(1, len(grid_levels) // 2)
            if active_orders_total >= max_active_orders:
                logger.debug("🚦 Límite de órdenes activas alcanzado, no se crea nueva compra")
                return None

            # Obtener órdenes de compra existentes
            existing_buy_orders = [order for order in existing_orders if order.side == 'buy' and order.status == 'open']
            existing_buy_prices = {order.price for order in existing_buy_orders}
            
            # Encontrar el nivel más alto sin orden dentro del límite
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
            
            # Límite de órdenes activas globales
            active_orders_total = len([o for o in existing_orders if o.status == 'open'])
            max_active_orders = max(1, len(grid_levels) // 2)
            if active_orders_total >= max_active_orders:
                logger.debug("🚦 Límite de órdenes activas alcanzado, no se crea nueva venta")
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

    def check_stop_loss_triggered(self, current_price: Decimal, last_buy_price: Decimal, config: GridConfig) -> bool:
        """
        Verifica si se debe activar el stop loss (4% por defecto).
        
        Args:
            current_price: Precio actual del mercado
            last_buy_price: Precio de la última orden de compra ejecutada
            config: Configuración del bot
            
        Returns:
            True si se debe activar stop loss
        """
        try:
            if not config.enable_stop_loss:
                return False
            
            # Calcular porcentaje de caída desde la última compra
            price_drop_percent = (last_buy_price - current_price) / last_buy_price * 100
            
            # Stop loss se activa si el precio cae más del porcentaje configurado por par
            stop_loss_percent = config.stop_loss_percent
            
            triggered = price_drop_percent >= stop_loss_percent
            
            if triggered:
                logger.warning(f"🚨 STOP LOSS ACTIVADO: Precio actual ${current_price:.4f}, última compra ${last_buy_price:.4f}, caída {price_drop_percent:.2f}%")
            
            return triggered
            
        except Exception as e:
            logger.error(f"❌ Error verificando stop loss: {e}")
            return False

    def check_trailing_up_triggered(self, current_price: Decimal, highest_sell_price: Decimal, config: GridConfig) -> bool:
        """
        Verifica si se debe activar el trailing up (5% por defecto).
        
        Args:
            current_price: Precio actual del mercado
            highest_sell_price: Precio más alto de las órdenes de venta activas
            config: Configuración del bot
            
        Returns:
            True si se debe activar trailing up
        """
        try:
            if not config.enable_trailing_up:
                return False
            
            # Calcular porcentaje de subida desde el nivel más alto de venta
            price_rise_percent = (current_price - highest_sell_price) / highest_sell_price * 100
            
            # Trailing up se activa si el precio sube más del 5% (configuración fija)
            trailing_up_percent = 5.0  # Por defecto 5%
            
            triggered = price_rise_percent >= trailing_up_percent
            
            if triggered:
                logger.info(f"📈 TRAILING UP ACTIVADO: Precio actual ${current_price:.4f}, nivel más alto venta ${highest_sell_price:.4f}, subida {price_rise_percent:.2f}%")
            
            return triggered
            
        except Exception as e:
            logger.error(f"❌ Error verificando trailing up: {e}")
            return False

    def get_highest_sell_price(self, active_orders: List[GridOrder]) -> Optional[Decimal]:
        """
        Obtiene el precio más alto de las órdenes de venta activas.
        
        Args:
            active_orders: Lista de órdenes activas
            
        Returns:
            Precio más alto de venta o None si no hay órdenes de venta
        """
        try:
            sell_orders = [order for order in active_orders if order.side == 'sell' and order.status == 'open']
            
            if not sell_orders:
                return None
            
            highest_price = max(order.price for order in sell_orders)
            return highest_price
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio más alto de venta: {e}")
            return None

    def get_last_buy_price(self, active_orders: List[GridOrder]) -> Optional[Decimal]:
        """
        Obtiene el precio de la última orden de compra ejecutada.
        
        Args:
            active_orders: Lista de órdenes activas
            
        Returns:
            Precio de la última compra o None si no hay compras
        """
        try:
            buy_orders = [order for order in active_orders if order.side == 'buy' and order.status == 'filled']
            
            if not buy_orders:
                return None
            
            # Ordenar por timestamp y obtener la más reciente
            latest_buy = max(buy_orders, key=lambda x: x.filled_at if x.filled_at else x.created_at if x.created_at else datetime.min)
            return latest_buy.price
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de última compra: {e}")
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

    def validate_capital_usage(self, config: GridConfig, exchange_service, current_price: Decimal) -> Dict[str, Any]:
        """
        Valida que el uso de capital no exceda lo configurado.
        RESPETA AISLAMIENTO DE CAPITAL: Cada bot solo usa su capital asignado.
        
        Args:
            config: Configuración del bot
            exchange_service: Servicio de exchange
            current_price: Precio actual
            
        Returns:
            Dict con información de validación de capital
        """
        try:
            configured_capital = Decimal(config.total_capital)
            
            # Obtener balance asignado al bot específico
            bot_balance = exchange_service.get_bot_allocated_balance(config)
            allocated_capital = bot_balance['allocated_capital']
            total_available = bot_balance['total_available_in_account']
            usable_capital = bot_balance['total_value_usdt']
            
            # Verificar si hay suficiente capital para aislamiento
            capital_sufficient = total_available >= allocated_capital
            
            # Calcular límites de órdenes
            max_order_value = usable_capital / 2  # 50% para órdenes de compra
            order_amount = self.calculate_order_amount(
                total_capital=float(usable_capital),
                grid_levels=config.grid_levels,
                current_price=current_price
            )
            
            validation_result = {
                'capital_sufficient': capital_sufficient,
                'configured_capital': configured_capital,
                'allocated_capital': allocated_capital,
                'available_capital': total_available,
                'usable_capital': usable_capital,
                'max_order_value': max_order_value,
                'recommended_order_amount': order_amount,
                'base_balance': bot_balance['base_balance'],
                'quote_balance': bot_balance['quote_balance'],
                'isolation_respected': capital_sufficient
            }
            
            logger.debug(f"🔒 Validación de capital {config.pair}: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error validando capital: {e}")
            return {
                'capital_sufficient': False,
                'configured_capital': Decimal('0'),
                'allocated_capital': Decimal('0'),
                'available_capital': Decimal('0'),
                'usable_capital': Decimal('0'),
                'max_order_value': Decimal('0'),
                'recommended_order_amount': Decimal('0'),
                'base_balance': Decimal('0'),
                'quote_balance': Decimal('0'),
                'isolation_respected': False
            }

    def can_create_order(self, side: str, amount: Decimal, price: Decimal, exchange_service, pair: str) -> Dict[str, Any]:
        """
        Verifica si se puede crear una orden con los balances actuales.
        
        Args:
            side: 'buy' o 'sell'
            amount: Cantidad de la orden
            price: Precio de la orden
            exchange_service: Servicio de exchange
            pair: Par de trading
            
        Returns:
            Dict con información de viabilidad de la orden
        """
        try:
            order_value = amount * price
            
            if side == 'buy':
                # Para compra necesitamos USDT
                required_balance = order_value
                available_balance = exchange_service.get_balance('USDT')
                currency_needed = 'USDT'
            else:
                # Para venta necesitamos la moneda base
                base_currency = pair.split('/')[0]
                required_balance = amount
                available_balance = exchange_service.get_balance(base_currency)
                currency_needed = base_currency
            
            can_create = available_balance >= required_balance
            
            result = {
                'can_create': can_create,
                'side': side,
                'required_balance': required_balance,
                'available_balance': available_balance,
                'currency_needed': currency_needed,
                'order_value': order_value,
                'sufficient_balance': can_create
            }
            
            if not can_create:
                logger.warning(f"⚠️ Balance insuficiente para {side}: necesario {required_balance} {currency_needed}, disponible {available_balance}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error verificando viabilidad de orden: {e}")
            return {
                'can_create': False,
                'side': side,
                'required_balance': Decimal('0'),
                'available_balance': Decimal('0'),
                'currency_needed': 'UNKNOWN',
                'order_value': Decimal('0'),
                'sufficient_balance': False
            } 