import ccxt
import time
from typing import Dict, List, Optional, Any
from app.core.logging_config import get_logger
from app.core.config import settings
from app.services.telegram_service import send_telegram_message, send_grid_trade_notification, send_grid_hourly_summary

logger = get_logger(__name__)

# Variables globales para mantener el estado
_exchange: Optional[ccxt.Exchange] = None
_active_orders: List[Dict[str, Any]] = []
_order_pairs: Dict[str, str] = {}  # Para trackear pares compra-venta


def get_binance_exchange():
    """
    Crea y retorna una instancia de Binance exchange usando las credenciales configuradas.
    """
    try:
        # Cargar las claves API desde settings
        api_key = settings.BINANCE_API_KEY
        api_secret = settings.BINANCE_API_SECRET
        
        if not api_key or not api_secret:
            raise ValueError("❌ Las claves API de Binance no están configuradas")
        
        # Configurar el exchange (Binance)
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,  # Cambiar a True para usar el testnet
            'enableRateLimit': True,
        })
        
        # Verificar la conexión
        balance = exchange.fetch_balance()
        logger.info("✅ Conexión con Binance establecida correctamente")
        logger.info(f"💵 Balance USDT: {balance.get('USDT', {}).get('free', 0)}")
        
        return exchange
        
    except Exception as e:
        logger.error(f"❌ Error al conectar con Binance: {e}")
        raise


def calculate_grid_levels(current_price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula los niveles de precio para la grilla de trading
    
    Args:
        current_price: Precio actual del asset
        config: Configuración del bot con grid_levels y price_range_percent
        
    Returns:
        Dict con las listas de precios de compra y venta
    """
    try:
        grid_levels = config['grid_levels']
        price_range_percent = config['price_range_percent']
        
        # Calcular el rango de precios
        price_range = current_price * (price_range_percent / 100)
        min_price = current_price - (price_range / 2)
        max_price = current_price + (price_range / 2)
        
        logger.info(f"📊 Rango de precios: ${min_price:.2f} - ${max_price:.2f}")
        
        # Dividir el número de niveles: mitad para compras, mitad para ventas
        buy_levels = grid_levels // 2
        sell_levels = grid_levels - buy_levels
        
        # Calcular precios de compra (por debajo del precio actual)
        buy_prices = []
        if buy_levels > 0:
            price_step = (current_price - min_price) / buy_levels
            for i in range(buy_levels):
                buy_price = current_price - price_step * (i + 1)
                buy_prices.append(round(buy_price, 2))
        
        # Calcular precios de venta (por encima del precio actual)
        sell_prices = []
        if sell_levels > 0:
            price_step = (max_price - current_price) / sell_levels
            for i in range(sell_levels):
                sell_price = current_price + price_step * (i + 1)
                sell_prices.append(round(sell_price, 2))
        
        logger.info(f"🟢 Precios de compra: {buy_prices}")
        logger.info(f"🔴 Precios de venta: {sell_prices}")
        
        return {
            'buy_prices': buy_prices,
            'sell_prices': sell_prices,
            'current_price': current_price,
            'range': {'min': min_price, 'max': max_price}
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculando niveles de grilla: {e}")
        raise


def create_grid_orders(config: Dict[str, str], exchange: ccxt.Exchange):
    """
    Calcula y coloca las órdenes iniciales en el mercado
    
    Args:
        config: Diccionario con la configuración del bot
        exchange: Instancia del exchange de Binance
    """
    global _active_orders
    
    try:
        logger.info("📋 Calculando y creando órdenes de la grilla...")
        
        pair = config['pair']
        total_capital = config['total_capital']
        current_price = exchange.fetch_ticker(pair)['last']
        
        logger.info(f"💹 Precio actual de {pair}: ${current_price}")
        
        # Calcular niveles de grilla
        grid_data = calculate_grid_levels(current_price, config)
        buy_prices = grid_data['buy_prices']
        
        # Calcular capital por orden de compra
        if len(buy_prices) > 0:
            capital_per_order = total_capital / len(buy_prices)
            logger.info(f"💰 Capital por orden: ${capital_per_order:.2f}")
            
            # Crear órdenes de compra
            for price in buy_prices:
                quantity = capital_per_order / price
                
                try:
                    # Crear orden de compra limitada
                    order = exchange.create_limit_buy_order(pair, quantity, price)
                    
                    order_info = {
                        'id': order['id'],
                        'type': 'buy',
                        'quantity': quantity,
                        'price': price,
                        'pair': pair,
                        'status': 'open',
                        'timestamp': order['timestamp']
                    }
                    
                    _active_orders.append(order_info)
                    logger.info(f"✅ Orden de compra creada: {quantity:.6f} {pair.split('/')[0]} a ${price}")
                    
                except Exception as e:
                    logger.error(f"❌ Error creando orden de compra a ${price}: {e}")
            
            # Enviar notificación de inicio
            message = f"🚀 <b>GRID BOT INICIADO</b>\n\n"
            message += f"📊 <b>Par:</b> {pair}\n"
            message += f"💰 <b>Capital:</b> ${total_capital}\n"
            message += f"🎯 <b>Niveles:</b> {config['grid_levels']}\n"
            message += f"📈 <b>Rango:</b> {config['price_range_percent']}%\n"
            message += f"💹 <b>Precio actual:</b> ${current_price:.2f}\n"
            message += f"🟢 <b>Órdenes de compra:</b> {len(buy_prices)}"
            
            send_telegram_message(message)
        
        else:
            logger.warning("⚠️ No se crearon órdenes de compra")
        
    except Exception as e:
        logger.error(f"❌ Error al crear órdenes de grilla: {e}")
        raise


def create_sell_order_after_buy(buy_order: Dict[str, Any], exchange: ccxt.Exchange):
    """
    Crea una orden de venta después de que se ejecute una compra
    
    Args:
        buy_order: Información de la orden de compra ejecutada
        exchange: Instancia del exchange
    """
    global _active_orders, _order_pairs
    
    try:
        pair = buy_order['pair']
        quantity = buy_order['quantity']
        buy_price = buy_order['price']
        
        # Calcular precio de venta con 1% de ganancia
        sell_price = buy_price * 1.01
        sell_price = round(sell_price, 2)
        
        # Crear orden de venta
        order = exchange.create_limit_sell_order(pair, quantity, sell_price)
        
        sell_order_info = {
            'id': order['id'],
            'type': 'sell',
            'quantity': quantity,
            'price': sell_price,
            'pair': pair,
            'status': 'open',
            'timestamp': order['timestamp'],
            'buy_price': buy_price  # Para calcular ganancia
        }
        
        _active_orders.append(sell_order_info)
        _order_pairs[order['id']] = buy_order['id']  # Relacionar venta con compra
        
        logger.info(f"✅ Orden de venta creada: {quantity:.6f} {pair.split('/')[0]} a ${sell_price} (ganancia: 1%)")
        
        # Enviar notificación de venta programada
        send_grid_trade_notification(sell_order_info, {'pair': pair})
        
    except Exception as e:
        logger.error(f"❌ Error creando orden de venta: {e}")


def monitor_and_replace_orders(config: Dict[str, str], exchange: ccxt.Exchange):
    """
    El bucle principal que correrá 24/7 para monitorear órdenes ejecutadas y colocar las nuevas
    
    Args:
        config: Diccionario con la configuración del bot
        exchange: Instancia del exchange de Binance
    """
    global _active_orders
    
    logger.info("🔄 Iniciando monitoreo de órdenes...")
    status_counter = 0  # Para enviar resumen cada hora
    trades_in_last_hour = 0  # Contador de trades en la última hora
    
    try:
        while True:
            logger.info("👀 Monitoreando órdenes activas...")
            
            # Verificar estado de cada orden activa
            orders_to_remove = []
            
            for i, order_info in enumerate(_active_orders):
                try:
                    # Obtener estado actual de la orden
                    order_status = exchange.fetch_order(order_info['id'], order_info['pair'])
                    
                    if order_status['status'] == 'closed':
                        logger.info(f"✅ Orden ejecutada: {order_info['type']} {order_info['quantity']:.6f} a ${order_info['price']}")
                        
                        # Incrementar contador de trades
                        trades_in_last_hour += 1
                        
                        # Enviar notificación de trade ejecutado (info importante)
                        send_grid_trade_notification(order_info, config)
                        
                        if order_info['type'] == 'buy':
                            # Si se ejecutó una compra, crear orden de venta
                            create_sell_order_after_buy(order_info, exchange)
                        
                        elif order_info['type'] == 'sell':
                            # Si se ejecutó una venta, crear nueva orden de compra al mismo precio original
                            buy_price = order_info.get('buy_price', order_info['price'] / 1.01)
                            quantity = order_info['quantity']
                            
                            try:
                                new_buy_order = exchange.create_limit_buy_order(
                                    order_info['pair'], 
                                    quantity, 
                                    buy_price
                                )
                                
                                new_order_info = {
                                    'id': new_buy_order['id'],
                                    'type': 'buy',
                                    'quantity': quantity,
                                    'price': buy_price,
                                    'pair': order_info['pair'],
                                    'status': 'open',
                                    'timestamp': new_buy_order['timestamp']
                                }
                                
                                _active_orders.append(new_order_info)
                                logger.info(f"✅ Nueva orden de compra creada: {quantity:.6f} a ${buy_price}")
                                
                            except Exception as e:
                                logger.error(f"❌ Error creando nueva orden de compra: {e}")
                        
                        # Marcar para eliminar de la lista de activas
                        orders_to_remove.append(i)
                
                except Exception as e:
                    logger.error(f"❌ Error verificando orden {order_info['id']}: {e}")
            
            # Eliminar órdenes ejecutadas de la lista de activas
            for i in reversed(orders_to_remove):
                _active_orders.pop(i)
            
            # Enviar resumen cada hora (120 ciclos = 1 hora)
            status_counter += 1
            if status_counter >= 120:
                # Solo enviar resumen si hubo actividad
                if trades_in_last_hour > 0:
                    send_grid_hourly_summary(_active_orders, config, trades_in_last_hour)
                    logger.info(f"📊 Resumen horario enviado - Trades ejecutados: {trades_in_last_hour}")
                
                # Resetear contadores
                status_counter = 0
                trades_in_last_hour = 0
            
            # Esperar 30 segundos antes del siguiente chequeo
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Deteniendo monitoreo por solicitud del usuario...")
    except Exception as e:
        logger.error(f"❌ Error en el monitoreo de órdenes: {e}")
        # Enviar notificación de error
        send_telegram_message(f"❌ <b>ERROR EN GRID BOT</b>\n\n{str(e)}")
        raise


def run_grid_trading_bot(config: Dict[str, Any]):
    """
    Función principal que orquesta todo el proceso del Grid Trading Bot
    
    Args:
        config: Diccionario con la configuración del bot
    """
    try:
        logger.info(f"🤖 Iniciando Grid Trading Bot para {config.get('pair', 'N/A')}")
        logger.info(f"💰 Capital total: ${config.get('total_capital', 0)}")
        logger.info(f"📊 Niveles de grilla: {config.get('grid_levels', 0)}")
        
        # Inicializar conexión con el exchange
        exchange = get_binance_exchange()
        
        # Paso 1: Crear órdenes iniciales de la grilla
        create_grid_orders(config, exchange)
        
        # Paso 2: Iniciar el monitoreo continuo
        monitor_and_replace_orders(config, exchange)
        
    except Exception as e:
        logger.error(f"❌ Error fatal en Grid Trading Bot: {e}")
        # Enviar notificación de error crítico
        send_telegram_message(f"🚨 <b>ERROR CRÍTICO EN GRID BOT</b>\n\n{str(e)}")
        raise
    finally:
        logger.info("🛑 Grid Trading Bot detenido") 