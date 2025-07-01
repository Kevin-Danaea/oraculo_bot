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
    MEJORADO: Agrega logging detallado y validaciones
    
    Args:
        exchange: Instancia del exchange
        pair: Par de trading (ej: 'ETH/USDT')
        
    Returns:
        Dict con balances de USDT y crypto
    """
    try:
        # Obtener balance completo del exchange
        balance = exchange.fetch_balance()
        crypto_symbol = pair.split('/')[0]  # ETH de ETH/USDT
        
        # Extraer balances específicos
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        crypto_balance = balance.get(crypto_symbol, {}).get('free', 0)
        
        # Obtener precio actual para calcular valor total
        ticker = exchange.fetch_ticker(pair)
        current_price = ticker['last']
        crypto_value = crypto_balance * current_price
        total_value = usdt_balance + crypto_value
        
        # LOGGING DETALLADO PARA DEBUGGING
        logger.info(f"💰 Balance detallado para {pair}:")
        logger.info(f"   USDT disponible: ${usdt_balance:.2f}")
        logger.info(f"   {crypto_symbol} disponible: {crypto_balance:.6f}")
        logger.info(f"   Precio actual {crypto_symbol}: ${current_price:.2f}")
        logger.info(f"   Valor {crypto_symbol}: ${crypto_value:.2f}")
        logger.info(f"   Total calculado: ${total_value:.2f}")
        
        # Validar que los valores sean razonables
        if usdt_balance < 0:
            logger.warning(f"⚠️ USDT balance negativo: ${usdt_balance:.2f}")
        if crypto_balance < 0:
            logger.warning(f"⚠️ {crypto_symbol} balance negativo: {crypto_balance:.6f}")
        if current_price <= 0:
            logger.error(f"❌ Precio inválido: ${current_price:.2f}")
        if total_value < 0:
            logger.error(f"❌ Total negativo: ${total_value:.2f}")
        
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


def calculate_pnl_with_explanation(balance: dict, initial_capital: float, mode: str = "UNKNOWN") -> dict:
    """
    Calcula P&L con explicación detallada y validaciones
    
    Args:
        balance: Dict con balance actual (de get_current_balance)
        initial_capital: Capital inicial configurado
        mode: Modo de trading (SANDBOX/PRODUCTIVO)
        
    Returns:
        Dict con P&L calculado y explicación
    """
    try:
        total_value = balance['total_value']
        usdt_balance = balance['usdt']
        crypto_value = balance['crypto_value']
        
        # Calcular P&L
        total_pnl = total_value - initial_capital
        
        # Calcular porcentaje con validación
        if initial_capital > 0:
            total_pnl_percentage = (total_pnl / initial_capital) * 100
        else:
            total_pnl_percentage = 0
            logger.warning("⚠️ Capital inicial es 0, no se puede calcular porcentaje")
        
        # Determinar icono
        pnl_icon = "📈" if total_pnl >= 0 else "📉"
        
        # LOGGING DETALLADO
        logger.info(f"📊 P&L calculado ({mode}):")
        logger.info(f"   Capital inicial: ${initial_capital:.2f}")
        logger.info(f"   Total actual: ${total_value:.2f}")
        logger.info(f"   P&L absoluto: ${total_pnl:.2f}")
        logger.info(f"   P&L porcentual: {total_pnl_percentage:.2f}%")
        logger.info(f"   Desglose: USDT ${usdt_balance:.2f} + {balance['crypto_symbol']} ${crypto_value:.2f}")
        
        return {
            'total_pnl': total_pnl,
            'total_pnl_percentage': total_pnl_percentage,
            'pnl_icon': pnl_icon,
            'initial_capital': initial_capital,
            'total_value': total_value,
            'mode': mode,
            'explanation': f"P&L = ${total_value:.2f} (actual) - ${initial_capital:.2f} (inicial) = ${total_pnl:.2f}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculando P&L: {e}")
        return {
            'total_pnl': 0,
            'total_pnl_percentage': 0,
            'pnl_icon': "❓",
            'initial_capital': initial_capital,
            'total_value': balance.get('total_value', 0),
            'mode': mode,
            'explanation': f"Error calculando P&L: {str(e)}"
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
    MEJORADO: Usa nueva función de P&L con explicación detallada
    
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
                
                # Obtener modo de trading para contexto
                from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
                mode = "PRODUCTIVO" if MODO_PRODUCTIVO else "SANDBOX"
                
                message += f"\n💰 <b>BALANCE ACTUAL ({mode}):</b>\n"
                message += f"💵 <b>USDT disponible:</b> ${balance['usdt']:.2f}\n"
                message += f"🪙 <b>{balance['crypto_symbol']} disponible:</b> {balance['crypto']:.6f}\n"
                message += f"💎 <b>Valor {balance['crypto_symbol']}:</b> ${balance['crypto_value']:.2f}\n"
                message += f"📊 <b>Total actual:</b> ${balance['total_value']:.2f}\n"
                
                # Calcular P&L usando nueva función mejorada
                initial_capital = config.get('total_capital', 0)
                if initial_capital > 0:
                    pnl_data = calculate_pnl_with_explanation(balance, initial_capital, mode)
                    
                    message += f"\n{pnl_data['pnl_icon']} <b>P&L Total:</b> ${pnl_data['total_pnl']:.2f} ({pnl_data['total_pnl_percentage']:.2f}%)\n"
                    message += f"💡 <i>Capital inicial: ${initial_capital:.2f} | {mode}</i>\n"
                else:
                    message += f"\n⚠️ <i>No se puede calcular P&L (capital inicial no configurado)</i>\n"
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener balance: {e}")
                message += f"\n⚠️ <i>Error obteniendo balance: {str(e)}</i>\n"
        
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
    MEJORADO: Usa nueva función de P&L con explicación detallada
    
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
                
                # Obtener modo de trading para contexto
                from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
                mode = "PRODUCTIVO" if MODO_PRODUCTIVO else "SANDBOX"
                
                message += f"\n💰 <b>BALANCE ACTUAL ({mode}):</b>\n"
                message += f"💵 <b>USDT disponible:</b> ${balance['usdt']:.2f}\n"
                message += f"🪙 <b>{balance['crypto_symbol']} disponible:</b> {balance['crypto']:.6f}\n"
                message += f"💎 <b>Valor {balance['crypto_symbol']}:</b> ${balance['crypto_value']:.2f}\n"
                message += f"📊 <b>Total actual:</b> ${balance['total_value']:.2f}\n"
                
                # Calcular P&L usando nueva función mejorada
                initial_capital = config.get('total_capital', 0)
                if initial_capital > 0:
                    pnl_data = calculate_pnl_with_explanation(balance, initial_capital, mode)
                    
                    message += f"\n{pnl_data['pnl_icon']} <b>P&L Total:</b> ${pnl_data['total_pnl']:.2f} ({pnl_data['total_pnl_percentage']:.2f}%)\n"
                    message += f"💡 <i>Capital inicial: ${initial_capital:.2f} | {mode}</i>\n"
                else:
                    message += f"\n⚠️ <i>No se puede calcular P&L (capital inicial no configurado)</i>\n"
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener balance en resumen: {e}")
                message += f"\n⚠️ <i>Error obteniendo balance: {str(e)}</i>\n"
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\n⏰ <i>{timestamp}</i>"
        
        return send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"❌ Error enviando resumen horario: {e}")
        return False 