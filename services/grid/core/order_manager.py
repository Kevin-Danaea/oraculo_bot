"""
Módulo de gestión de órdenes del Grid Trading Bot.
Maneja creación, cancelación y procesamiento de órdenes de compra/venta.
"""

import ccxt
import time
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from shared.services.logging_config import get_logger
from .config_manager import PROFIT_PERCENTAGE, ORDER_RETRY_ATTEMPTS
from .grid_calculator import calculate_order_quantity

logger = get_logger(__name__)


def create_order_with_retry(exchange: ccxt.Exchange, order_type: Literal['buy', 'sell'], pair: str, 
                          quantity: float, price: float, retries: int = ORDER_RETRY_ATTEMPTS) -> Optional[Dict]:
    """
    Crea una orden con reintentos en caso de fallo
    
    Args:
        exchange: Instancia del exchange
        order_type: 'buy' o 'sell'
        pair: Par de trading
        quantity: Cantidad
        price: Precio
        retries: Número de reintentos
        
    Returns:
        Información de la orden creada o None si falla
    """
    for attempt in range(retries):
        try:
            # Type cast para resolver el error del linter con ccxt OrderSide
            order = exchange.create_limit_order(pair, order_type, quantity, price)  # type: ignore
            logger.info(f"✅ Orden {order_type} creada: {quantity:.6f} a ${price}")
            return order
        except Exception as e:
            logger.error(f"❌ Intento {attempt + 1} falló: {e}")
            if attempt < retries - 1:
                time.sleep(1)  # Esperar 1 segundo antes del siguiente intento
    
    logger.error(f"❌ No se pudo crear orden después de {retries} intentos")
    return None


def create_initial_buy_orders(exchange: ccxt.Exchange, config: Dict[str, Any], 
                            grid_prices: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Crea las órdenes de compra iniciales
    
    Args:
        exchange: Instancia del exchange
        config: Configuración del bot
        grid_prices: Precios calculados de la grilla
        
    Returns:
        Lista de órdenes creadas exitosamente
    """
    active_orders = []
    buy_prices = grid_prices['buy_prices']
    
    if not buy_prices:
        logger.warning("⚠️ No hay precios de compra para crear órdenes")
        return active_orders
    
    try:
        pair = config['pair']
        total_capital = config['total_capital']
        capital_per_order = total_capital / len(buy_prices)
        
        logger.info(f"💰 Capital por orden: ${capital_per_order:.2f}")
        
        successful_orders = 0
        for price in buy_prices:
            quantity = calculate_order_quantity(capital_per_order, price)
            
            order = create_order_with_retry(exchange, 'buy', pair, quantity, price)
            if order:
                order_info = {
                    'id': order['id'],
                    'type': 'buy',
                    'quantity': quantity,
                    'price': price,
                    'pair': pair,
                    'status': 'open',
                    'timestamp': order['timestamp'],
                    'created_at': datetime.now().isoformat()
                }
                active_orders.append(order_info)
                successful_orders += 1
            
        logger.info(f"✅ Órdenes de compra creadas: {successful_orders}/{len(buy_prices)}")
        
        return active_orders
        
    except Exception as e:
        logger.error(f"❌ Error creando órdenes iniciales: {e}")
        return active_orders


def create_sell_order_after_buy(exchange: ccxt.Exchange, buy_order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Crea orden de venta después de ejecutarse una compra
    
    Args:
        exchange: Instancia del exchange
        buy_order: Información de la orden de compra ejecutada
        
    Returns:
        Información de la orden de venta creada o None
    """
    try:
        pair = buy_order['pair']
        quantity = buy_order['quantity']
        buy_price = buy_order['price']
        
        # Calcular precio de venta con ganancia
        sell_price = buy_price * (1 + PROFIT_PERCENTAGE)
        sell_price = round(sell_price, 2)
        
        order = create_order_with_retry(exchange, 'sell', pair, quantity, sell_price)
        if not order:
            return None
            
        sell_order_info = {
            'id': order['id'],
            'type': 'sell',
            'quantity': quantity,
            'price': sell_price,
            'pair': pair,
            'status': 'open',
            'timestamp': order['timestamp'],
            'buy_price': buy_price,
            'buy_order_id': buy_order['id'],
            'created_at': datetime.now().isoformat()
        }
        
        # Calcular ganancia esperada
        profit = (sell_price - buy_price) * quantity
        logger.info(f"💰 Orden venta creada: {quantity:.6f} a ${sell_price} (ganancia esperada: ${profit:.2f})")
        
        return sell_order_info
        
    except Exception as e:
        logger.error(f"❌ Error creando orden de venta: {e}")
        return None


def create_replacement_buy_order(exchange: ccxt.Exchange, sell_order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Crea una nueva orden de compra después de ejecutarse una venta
    
    Args:
        exchange: Instancia del exchange
        sell_order: Información de la orden de venta ejecutada
        
    Returns:
        Información de la nueva orden de compra o None
    """
    try:
        pair = sell_order['pair']
        quantity = sell_order['quantity']
        original_buy_price = sell_order.get('buy_price', sell_order['price'] * 0.99)
        
        order = create_order_with_retry(exchange, 'buy', pair, quantity, original_buy_price)
        if not order:
            return None
            
        buy_order_info = {
            'id': order['id'],
            'type': 'buy',
            'quantity': quantity,
            'price': original_buy_price,
            'pair': pair,
            'status': 'open',
            'timestamp': order['timestamp'],
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"🔄 Nueva orden compra creada: {quantity:.6f} a ${original_buy_price}")
        
        return buy_order_info
        
    except Exception as e:
        logger.error(f"❌ Error creando orden de compra de reemplazo: {e}")
        return None


__all__ = [
    'create_order_with_retry',
    'create_initial_buy_orders',
    'create_sell_order_after_buy',
    'create_replacement_buy_order'
] 