"""
Módulo de gestión de posiciones del Trend Trading Bot.
Ejecuta órdenes de compra/venta según las instrucciones del cerebro.
"""

import ccxt
from typing import Dict, Any
from datetime import datetime
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


def execute_market_buy(exchange: ccxt.Exchange, pair: str, capital: float, 
                      current_price: float) -> Dict[str, Any]:
    """
    Ejecuta una orden de compra a mercado.
    
    Args:
        exchange: Instancia del exchange
        pair: Par de trading
        capital: Capital disponible en USDT
        current_price: Precio actual (para cálculo de cantidad)
        
    Returns:
        Diccionario con resultado de la orden
    """
    try:
        # Calcular cantidad (95% del capital para dejar margen)
        amount = (capital * 0.95) / current_price
        amount = round(amount, 6)
        
        logger.info(f"🛒 Ejecutando compra: {amount:.6f} {pair} con ${capital:.2f}")
        
        # Ejecutar orden de mercado
        order = exchange.create_market_order(
            symbol=pair,
            side='buy',
            amount=amount
        )
        
        # Obtener detalles de la orden ejecutada
        order_id = order['id']
        filled_order = exchange.fetch_order(order_id, pair)
        
        # Extraer información relevante
        executed_price = filled_order['average'] if filled_order['average'] else filled_order['price']
        executed_amount = filled_order['filled']
        cost = filled_order['cost']
        
        logger.info(f"✅ Compra ejecutada: {executed_amount:.6f} a ${executed_price:.2f} (Total: ${cost:.2f})")
        
        return {
            'success': True,
            'order_id': order_id,
            'price': executed_price,
            'amount': executed_amount,
            'cost': cost,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando compra: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def execute_market_sell(exchange: ccxt.Exchange, pair: str, amount: float,
                       current_price: float) -> Dict[str, Any]:
    """
    Ejecuta una orden de venta a mercado.
    
    Args:
        exchange: Instancia del exchange
        pair: Par de trading
        amount: Cantidad a vender
        current_price: Precio actual (para logging)
        
    Returns:
        Diccionario con resultado de la orden
    """
    try:
        # Obtener balance real de crypto
        crypto_symbol = pair.split('/')[0]
        balance = exchange.fetch_balance()
        available = balance.get(crypto_symbol, {}).get('free', 0)
        
        # Usar el menor entre lo solicitado y lo disponible
        sell_amount = min(amount, available * 0.99)  # 99% para evitar errores de precisión
        
        if sell_amount < 0.001:
            raise ValueError(f"Balance insuficiente: {available:.6f} {crypto_symbol}")
        
        logger.info(f"💸 Ejecutando venta: {sell_amount:.6f} {pair} a mercado")
        
        # Ejecutar orden de mercado
        order = exchange.create_market_order(
            symbol=pair,
            side='sell',
            amount=sell_amount
        )
        
        # Obtener detalles de la orden ejecutada
        order_id = order['id']
        filled_order = exchange.fetch_order(order_id, pair)
        
        # Extraer información relevante
        executed_price = filled_order['average'] if filled_order['average'] else filled_order['price']
        executed_amount = filled_order['filled']
        proceeds = filled_order['cost']
        
        logger.info(f"✅ Venta ejecutada: {executed_amount:.6f} a ${executed_price:.2f} (Total: ${proceeds:.2f})")
        
        return {
            'success': True,
            'order_id': order_id,
            'price': executed_price,
            'amount': executed_amount,
            'proceeds': proceeds,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando venta: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def update_position_tracking(state: Dict[str, Any], current_price: float, 
                           config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza el tracking básico de la posición.
    
    Args:
        state: Estado actual de la posición
        current_price: Precio actual
        config: Configuración del bot
        
    Returns:
        Estado actualizado
    """
    try:
        updated_state = state.copy()
        
        # Actualizar precio más alto
        if current_price > state.get('highest_price', 0):
            updated_state['highest_price'] = current_price
            
            # Actualizar trailing stop (20% desde el máximo)
            new_stop = current_price * 0.8
            if new_stop > state.get('stop_price', 0):
                updated_state['stop_price'] = new_stop
                logger.info(f"🛡️ Stop loss actualizado: ${new_stop:.2f}")
        
        # Calcular P&L no realizado
        entry_price = state['entry_price']
        position_size = state['position_size']
        unrealized_pnl = (current_price - entry_price) * position_size
        unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        updated_state['unrealized_pnl'] = unrealized_pnl
        updated_state['unrealized_pnl_pct'] = unrealized_pnl_pct
        updated_state['current_price'] = current_price
        updated_state['last_update'] = datetime.now().isoformat()
        
        # Verificar si tocó el stop loss
        if current_price <= updated_state.get('stop_price', 0):
            logger.warning(f"⚠️ ALERTA: Precio ${current_price:.2f} cerca/debajo del stop ${updated_state['stop_price']:.2f}")
            updated_state['stop_loss_alert'] = True
        
        return updated_state
        
    except Exception as e:
        logger.error(f"❌ Error actualizando tracking: {e}")
        return state


__all__ = [
    'execute_market_buy',
    'execute_market_sell',
    'update_position_tracking'
] 