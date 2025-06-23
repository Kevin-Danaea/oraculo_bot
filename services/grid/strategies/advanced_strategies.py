"""
Estrategias Avanzadas V2 - Stop-Loss y Trailing Up
Módulo especializado para manejar estrategias defensivas y ofensivas del grid bot.
Separación clara de responsabilidades para mantener el código escalable.
"""

import ccxt
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from shared.services.logging_config import get_logger
from shared.services.telegram_service import send_telegram_message

logger = get_logger(__name__)


def should_trigger_stop_loss(current_price: float, lowest_buy_price: float, 
                           stop_loss_percent: float, enable_stop_loss: bool) -> bool:
    """
    Determina si se debe activar el stop-loss basado en el precio actual.
    
    Args:
        current_price: Precio actual del activo
        lowest_buy_price: Precio de la orden de compra más baja activa
        stop_loss_percent: Porcentaje de stop-loss configurado
        enable_stop_loss: Si el stop-loss está habilitado
        
    Returns:
        True si se debe activar el stop-loss
    """
    if not enable_stop_loss or not lowest_buy_price:
        return False
    
    stop_loss_threshold = lowest_buy_price * (1 - stop_loss_percent / 100)
    should_trigger = current_price <= stop_loss_threshold
    
    if should_trigger:
        logger.warning(f"🚨 Stop-Loss detectado: precio actual ${current_price:.2f} <= threshold ${stop_loss_threshold:.2f}")
    
    return should_trigger


def should_trigger_trailing_up(current_price: float, highest_sell_price: float, 
                             enable_trailing_up: bool) -> bool:
    """
    Determina si se debe activar el trailing up basado en el precio actual.
    
    Args:
        current_price: Precio actual del activo
        highest_sell_price: Precio de la orden de venta más alta del grid
        enable_trailing_up: Si el trailing up está habilitado
        
    Returns:
        True si se debe activar el trailing up
    """
    if not enable_trailing_up or not highest_sell_price:
        return False
    
    should_trigger = current_price >= highest_sell_price
    
    if should_trigger:
        logger.info(f"📈 Trailing Up detectado: precio actual ${current_price:.2f} >= límite superior ${highest_sell_price:.2f}")
    
    return should_trigger


def execute_stop_loss_strategy(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                             config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta la estrategia de stop-loss: cancelar todo, vender todo, detener bot.
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        
    Returns:
        Resultado de la ejecución con métricas
    """
    try:
        logger.warning("🚨 ========== EJECUTANDO STOP-LOSS STRATEGY ==========")
        
        pair = config['pair']
        cancelled_orders = 0
        total_crypto_to_sell = 0.0
        realized_loss = 0.0
        
        # 1. Cancelar TODAS las órdenes (compra y venta)
        for order_info in active_orders:
            try:
                exchange.cancel_order(order_info['id'], pair)
                cancelled_orders += 1
                logger.info(f"🚫 Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
            except Exception as e:
                logger.error(f"❌ Error cancelando orden {order_info['id']}: {e}")
        
        # 2. Obtener balance actual de la crypto
        try:
            balance = exchange.fetch_balance()
            crypto_symbol = pair.split('/')[0]  # ETH de ETH/USDT
            crypto_balance = balance.get(crypto_symbol, {}).get('free', 0)
            
            if crypto_balance > 0.001:  # Si tenemos crypto para vender
                # 3. Vender TODO el balance de crypto a precio de mercado
                current_price = exchange.fetch_ticker(pair)['last']
                sell_order = exchange.create_market_order(pair, 'sell', crypto_balance)
                
                total_crypto_to_sell = crypto_balance
                realized_loss = calculate_estimated_loss(active_orders, current_price, config)
                
                logger.warning(f"💸 Venta de emergencia: {crypto_balance:.6f} {crypto_symbol} a precio de mercado ${current_price:.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando venta de emergencia: {e}")
        
        # 4. Preparar resultado y notificación
        result = {
            'success': True,
            'cancelled_orders': cancelled_orders,
            'crypto_sold': total_crypto_to_sell,
            'estimated_loss': realized_loss,
            'timestamp': datetime.now().isoformat(),
            'reason': 'stop_loss_triggered'
        }
        
        # 5. Enviar notificación urgente
        send_stop_loss_notification(config, result)
        
        logger.warning("🛑 Stop-Loss ejecutado completamente - Bot debe detenerse")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error crítico ejecutando stop-loss: {e}")
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN STOP-LOSS</b>\n\n{str(e)}")
        return {'success': False, 'error': str(e)}


def execute_trailing_up_strategy(exchange: ccxt.Exchange, active_orders: List[Dict[str, Any]], 
                                config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Ejecuta la estrategia de trailing up: cancelar órdenes, recalcular grid, nuevas órdenes.
    
    Args:
        exchange: Instancia del exchange
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        
    Returns:
        Tuple de (nuevas_órdenes_activas, éxito)
    """
    try:
        logger.info("📈 ========== EJECUTANDO TRAILING UP STRATEGY ==========")
        
        pair = config['pair']
        cancelled_orders = 0
        
        # 1. Cancelar TODAS las órdenes del grid antiguo
        for order_info in active_orders:
            try:
                exchange.cancel_order(order_info['id'], pair)
                cancelled_orders += 1
                logger.info(f"🚫 Orden cancelada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
            except Exception as e:
                logger.error(f"❌ Error cancelando orden {order_info['id']}: {e}")
        
        # 2. Obtener precio actual y recalcular grid
        current_price = exchange.fetch_ticker(pair)['last']
        logger.info(f"💹 Nuevo precio base para trailing up: ${current_price:.2f}")
        
        # 3. Importar funciones necesarias para recalcular grid
        from ..strategies.grid_strategy import calculate_grid_prices
        from ..core.order_manager import create_initial_buy_orders
        
        # 4. Calcular nuevos precios de grid centrados en el precio actual
        new_grid_prices = calculate_grid_prices(current_price, config)
        
        # 5. Crear nuevas órdenes basadas en balances actuales
        new_active_orders = create_rebalanced_orders(exchange, config, new_grid_prices, current_price)
        
        # 6. Enviar notificación de trailing up
        send_trailing_up_notification(config, current_price, len(new_active_orders), cancelled_orders)
        
        logger.info(f"✅ Trailing Up completado: {len(new_active_orders)} nuevas órdenes creadas")
        return new_active_orders, True
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando trailing up: {e}")
        send_telegram_message(f"🚨 <b>ERROR EN TRAILING UP</b>\n\n{str(e)}")
        return active_orders, False


def create_rebalanced_orders(exchange: ccxt.Exchange, config: Dict[str, Any], 
                           grid_prices: Dict[str, Any], current_price: float) -> List[Dict[str, Any]]:
    """
    Crea órdenes rebalanceadas usando los balances actuales (crypto + USDT).
    Optimización: no vender crypto para recomprar, usar lo que ya tenemos.
    
    Args:
        exchange: Instancia del exchange
        config: Configuración del bot
        grid_prices: Precios calculados del nuevo grid
        current_price: Precio actual
        
    Returns:
        Lista de nuevas órdenes activas
    """
    from ..core.order_manager import create_order_with_retry
    from ..strategies.grid_strategy import calculate_order_quantity, calculate_dynamic_profit_percentage
    
    new_orders = []
    pair = config['pair']
    crypto_symbol = pair.split('/')[0]
    
    try:
        # Obtener balances actuales
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        crypto_balance = balance.get(crypto_symbol, {}).get('free', 0)
        
        logger.info(f"💰 Balances actuales: {usdt_balance:.2f} USDT, {crypto_balance:.6f} {crypto_symbol}")
        
        # Crear órdenes de compra con USDT disponible
        buy_prices = grid_prices['buy_prices']
        if buy_prices and usdt_balance > 10:  # Mínimo $10 para operar
            capital_per_buy_order = usdt_balance / len(buy_prices)
            
            for price in buy_prices:
                if price < current_price:  # Solo órdenes de compra por debajo del precio actual
                    quantity = calculate_order_quantity(capital_per_buy_order, price)
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
                        new_orders.append(order_info)
        
        # Crear órdenes de venta con crypto disponible
        if crypto_balance > 0.001:  # Mínimo para crear órdenes
            profit_percentage = calculate_dynamic_profit_percentage(config)
            
            # Distribuir crypto entre órdenes de venta
            sell_prices = [p for p in grid_prices.get('sell_prices', []) if p > current_price]
            if sell_prices:
                crypto_per_sell_order = crypto_balance / len(sell_prices)
                
                for price in sell_prices:
                    if crypto_per_sell_order >= 0.001:  # Cantidad mínima
                        order = create_order_with_retry(exchange, 'sell', pair, crypto_per_sell_order, price)
                        
                        if order:
                            order_info = {
                                'id': order['id'],
                                'type': 'sell',
                                'quantity': crypto_per_sell_order,
                                'price': price,
                                'pair': pair,
                                'status': 'open',
                                'timestamp': order['timestamp'],
                                'created_at': datetime.now().isoformat()
                            }
                            new_orders.append(order_info)
        
        return new_orders
        
    except Exception as e:
        logger.error(f"❌ Error creando órdenes rebalanceadas: {e}")
        return []


def calculate_estimated_loss(active_orders: List[Dict[str, Any]], current_price: float, 
                           config: Dict[str, Any]) -> float:
    """
    Calcula la pérdida estimada en USD para el stop-loss.
    
    Args:
        active_orders: Órdenes activas
        current_price: Precio actual
        config: Configuración del bot
        
    Returns:
        Pérdida estimada en USD
    """
    try:
        total_loss = 0.0
        
        for order in active_orders:
            if order['type'] == 'buy' and order['status'] == 'open':
                # Órdenes de compra que están por encima del precio actual
                if order['price'] > current_price:
                    loss_per_unit = order['price'] - current_price
                    total_loss += loss_per_unit * order['quantity']
        
        return total_loss
        
    except Exception as e:
        logger.error(f"❌ Error calculando pérdida estimada: {e}")
        return 0.0


def send_stop_loss_notification(config: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Envía notificación urgente de stop-loss activado"""
    try:
        pair = config['pair']
        message = f"🚨 <b>STOP-LOSS ACTIVADO</b> 🚨\n\n"
        message += f"📊 <b>Par:</b> {pair}\n"
        message += f"🚫 <b>Órdenes canceladas:</b> {result['cancelled_orders']}\n"
        message += f"💸 <b>Crypto vendida:</b> {result['crypto_sold']:.6f}\n"
        message += f"📉 <b>Pérdida estimada:</b> ${result['estimated_loss']:.2f} USD\n\n"
        message += f"🛑 <b>El bot se ha DETENIDO automáticamente</b>\n"
        message += f"⚠️ <b>Requiere intervención manual para reiniciar</b>\n\n"
        message += f"🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de stop-loss: {e}")


def send_trailing_up_notification(config: Dict[str, Any], new_price: float, 
                                new_orders: int, cancelled_orders: int) -> None:
    """Envía notificación de trailing up ejecutado"""
    try:
        pair = config['pair']
        message = f"📈 <b>TRAILING UP EJECUTADO</b>\n\n"
        message += f"📊 <b>Par:</b> {pair}\n"
        message += f"💹 <b>Nuevo precio base:</b> ${new_price:.2f}\n"
        message += f"🚫 <b>Órdenes canceladas:</b> {cancelled_orders}\n"
        message += f"🆕 <b>Nuevas órdenes:</b> {new_orders}\n\n"
        message += f"🎯 <b>Grid reposicionado exitosamente</b>\n"
        message += f"🚀 <b>Siguiendo tendencia alcista</b>\n\n"
        message += f"🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
        
        send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de trailing up: {e}")


__all__ = [
    'should_trigger_stop_loss',
    'should_trigger_trailing_up', 
    'execute_stop_loss_strategy',
    'execute_trailing_up_strategy',
    'create_rebalanced_orders',
    'calculate_estimated_loss'
] 