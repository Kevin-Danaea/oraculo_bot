"""
Servicio de notificaciones de Telegram compartido entre todos los microservicios.
Centraliza el envío de notificaciones y mensajes.
"""
from typing import Optional
import requests
import ccxt
from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


def get_current_balance(exchange: ccxt.Exchange, pair: str) -> dict:
    """
    Obtiene el balance actual de USDT y la crypto del par especificado
    
    Args:
        exchange: Instancia del exchange
        pair: Par de trading (ej: 'ETH/USDT')
        
    Returns:
        Dict con balances de USDT y crypto
    """
    try:
        balance = exchange.fetch_balance()
        crypto_symbol = pair.split('/')[0]  # ETH de ETH/USDT
        
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        crypto_balance = balance.get(crypto_symbol, {}).get('free', 0)
        
        # Obtener precio actual para calcular valor total
        ticker = exchange.fetch_ticker(pair)
        current_price = ticker['last']
        crypto_value = crypto_balance * current_price
        total_value = usdt_balance + crypto_value
        
        return {
            'usdt': usdt_balance,
            'crypto': crypto_balance,
            'crypto_symbol': crypto_symbol,
            'current_price': current_price,
            'crypto_value': crypto_value,
            'total_value': total_value
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo balance: {e}")
        return {
            'usdt': 0,
            'crypto': 0,
            'crypto_symbol': pair.split('/')[0],
            'current_price': 0,
            'crypto_value': 0,
            'total_value': 0
        }


def send_telegram_message(message: str):
    """
    Envía un mensaje a Telegram usando la API de bots
    
    Args:
        message: Mensaje a enviar
    """
    try:
        # Verificar configuración
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("⚠️ No se han configurado las credenciales de Telegram")
            return False
        
        # URL de la API de Telegram
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Datos del mensaje
        data = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'  # Para formateo HTML
        }
        
        # Enviar mensaje
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Mensaje enviado a Telegram correctamente")
            return True
        else:
            logger.error(f"❌ Error enviando mensaje a Telegram: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
        return False


def send_service_startup_notification(service_name: str, features = None):
    """
    Envía notificación cuando se inicializa un servicio específico
    Nueva función más flexible que reemplaza send_system_startup_notification
    
    Args:
        service_name: Nombre del servicio (ej: "Servicio de Noticias", "Grid Trading Bot")
        features: Lista de características activas (opcional)
    """
    try:
        message = f"🚀 <b>{service_name.upper()} INICIADO</b>\n\n"
        
        if features is not None:
            for feature in features:
                message += f"✅ {feature}\n"
            message += "\n"
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"⏰ <i>{timestamp}</i>"
        message += f"\n\n🟢 <i>Servicio operativo y listo para funcionar</i>"
        
        return send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de inicio: {e}")
        return False


def send_grid_trade_notification(order_info: dict, config: dict, exchange: Optional[ccxt.Exchange] = None):
    """
    Envía notificación específica para trades del grid bot con balance actual
    
    Args:
        order_info: Información de la orden ejecutada
        config: Configuración del bot
        exchange: Instancia del exchange para obtener balance (opcional)
    """
    try:
        pair = config['pair']
        order_type = order_info['type'].upper()
        quantity = order_info['quantity']
        price = order_info['price']
        
        # Formatear mensaje con HTML
        message = f"<b>🤖 GRID BOT - {order_type} EJECUTADA</b>\n\n"
        message += f"📊 <b>Par:</b> {pair}\n"
        message += f"💱 <b>Cantidad:</b> {quantity:.6f} {pair.split('/')[0]}\n"
        message += f"💰 <b>Precio:</b> ${price:.2f}\n"
        
        # Si es venta, calcular ganancia
        if order_type == "SELL" and 'buy_price' in order_info:
            buy_price = order_info['buy_price']
            profit = (price - buy_price) * quantity
            profit_percentage = ((price - buy_price) / buy_price) * 100
            
            message += f"📈 <b>Precio de compra:</b> ${buy_price:.2f}\n"
            message += f"💵 <b>Ganancia:</b> ${profit:.2f} ({profit_percentage:.2f}%)\n"
        
        # Agregar balance actual si tenemos acceso al exchange
        if exchange:
            try:
                balance = get_current_balance(exchange, pair)
                message += f"\n💰 <b>BALANCE ACTUAL:</b>\n"
                message += f"💵 <b>USDT:</b> ${balance['usdt']:.2f}\n"
                message += f"🪙 <b>{balance['crypto_symbol']}:</b> {balance['crypto']:.6f}\n"
                message += f"💎 <b>Valor {balance['crypto_symbol']}:</b> ${balance['crypto_value']:.2f}\n"
                message += f"📊 <b>Total:</b> ${balance['total_value']:.2f}\n"
                
                # Calcular P&L si tenemos información de compra
                if order_type == "SELL" and 'buy_price' in order_info:
                    # Calcular P&L total aproximado
                    initial_capital = config.get('total_capital', 0)
                    if initial_capital > 0:
                        total_pnl = balance['total_value'] - initial_capital
                        total_pnl_percentage = (total_pnl / initial_capital) * 100
                        pnl_icon = "📈" if total_pnl >= 0 else "📉"
                        message += f"{pnl_icon} <b>P&L Total:</b> ${total_pnl:.2f} ({total_pnl_percentage:.2f}%)\n"
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener balance: {e}")
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\n⏰ <i>{timestamp}</i>"
        
        # Enviar mensaje
        return send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de trade: {e}")
        return False


def send_grid_hourly_summary(active_orders: list, config: dict, trades_count: int, exchange: Optional[ccxt.Exchange] = None):
    """
    Envía resumen horario del grid bot con información de actividad y balance
    
    Args:
        active_orders: Lista de órdenes activas
        config: Configuración del bot
        trades_count: Número de trades ejecutados en la última hora
        exchange: Instancia del exchange para obtener balance (opcional)
    """
    try:
        buy_orders = [o for o in active_orders if o['type'] == 'buy']
        sell_orders = [o for o in active_orders if o['type'] == 'sell']
        
        message = f"<b>🕐 RESUMEN HORARIO - GRID BOT</b>\n\n"
        message += f"📈 <b>Par:</b> {config['pair']}\n"
        message += f"⚡ <b>Actividad:</b> {trades_count} trades ejecutados\n\n"
        
        message += f"📊 <b>Estado actual:</b>\n"
        message += f"🟢 Órdenes de compra: {len(buy_orders)}\n"
        message += f"🔴 Órdenes de venta: {len(sell_orders)}\n"
        message += f"📋 Total activas: {len(active_orders)}\n\n"
        
        # Mostrar rangos de precios de las órdenes activas
        if buy_orders:
            min_buy = min(o['price'] for o in buy_orders)
            max_buy = max(o['price'] for o in buy_orders)
            message += f"🟢 <b>Rango compras:</b> ${min_buy:.2f} - ${max_buy:.2f}\n"
        
        if sell_orders:
            min_sell = min(o['price'] for o in sell_orders)
            max_sell = max(o['price'] for o in sell_orders)
            message += f"🔴 <b>Rango ventas:</b> ${min_sell:.2f} - ${max_sell:.2f}\n"
        
        # Agregar balance actual si tenemos acceso al exchange
        if exchange:
            try:
                balance = get_current_balance(exchange, config['pair'])
                message += f"\n💰 <b>BALANCE ACTUAL:</b>\n"
                message += f"💵 <b>USDT:</b> ${balance['usdt']:.2f}\n"
                message += f"🪙 <b>{balance['crypto_symbol']}:</b> {balance['crypto']:.6f}\n"
                message += f"💎 <b>Valor {balance['crypto_symbol']}:</b> ${balance['crypto_value']:.2f}\n"
                message += f"📊 <b>Total:</b> ${balance['total_value']:.2f}\n"
                
                # Calcular P&L total
                initial_capital = config.get('total_capital', 0)
                if initial_capital > 0:
                    total_pnl = balance['total_value'] - initial_capital
                    total_pnl_percentage = (total_pnl / initial_capital) * 100
                    pnl_icon = "📈" if total_pnl >= 0 else "📉"
                    message += f"{pnl_icon} <b>P&L Total:</b> ${total_pnl:.2f} ({total_pnl_percentage:.2f}%)\n"
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener balance en resumen: {e}")
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\n⏰ <i>{timestamp}</i>"
        
        return send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando resumen horario: {e}")
        return False 