"""
Servicio de Telegram especializado para funcionalidades de trading.
Extiende TelegramBaseService con funciones específicas para notificaciones de trading.
"""
import ccxt
from typing import Optional, Dict, List
from .telegram_base import TelegramBaseService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)


class TelegramTradingService(TelegramBaseService):
    """
    Servicio de Telegram especializado para trading.
    Incluye funciones específicas para notificaciones de grid trading y análisis.
    """
    
    def __init__(self):
        """Inicializa el servicio de trading de Telegram."""
        super().__init__()
    
    def get_current_balance(self, exchange: ccxt.Exchange, pair: str) -> dict:
        """
        Obtiene el balance actual de USDT y la crypto del par especificado.
        
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
            
            # LOGGING DETALLADO
            logger.info(f"💰 Balance detallado para {pair}:")
            logger.info(f"   USDT disponible: ${usdt_balance:.2f}")
            logger.info(f"   {crypto_symbol} disponible: {crypto_balance:.6f}")
            logger.info(f"   Precio actual {crypto_symbol}: ${current_price:.2f}")
            logger.info(f"   Valor {crypto_symbol}: ${crypto_value:.2f}")
            logger.info(f"   Total calculado: ${total_value:.2f}")
            
            # Validaciones
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

    def calculate_pnl_with_explanation(self, balance: dict, initial_capital: float, mode: str = "UNKNOWN") -> dict:
        """
        Calcula P&L con explicación detallada y validaciones.
        
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

    def send_service_startup_notification(self, service_name: str, features: Optional[List[str]] = None):
        """
        Envía notificación de inicio de servicio.
        
        Args:
            service_name: Nombre del servicio
            features: Lista de características del servicio
        """
        features_text = ""
        if features:
            features_text = "\n".join([f"   • {feature}" for feature in features])
            features_text = f"\n\n<b>🎯 Características:</b>\n{features_text}"
        
        message = f"""
        🚀 <b>{service_name}</b> iniciado correctamente

        <b>📅 Estado:</b> ✅ Operativo
        <b>🕐 Timestamp:</b> {logger.handlers[0].format(logger.makeRecord('', 0, '', 0, '', (), None)).split(']')[0][1:] if logger.handlers else 'N/A'}
        {features_text}

        El servicio está listo para procesar solicitudes.
        """.strip()
        
        self.send_message(message)

    def send_grid_trade_notification(self, order_info: dict, config: dict, exchange: Optional[ccxt.Exchange] = None):
        """
        Envía notificación de trade del grid bot.
        
        Args:
            order_info: Información de la orden ejecutada
            config: Configuración del bot
            exchange: Instancia del exchange (opcional para calcular balance)
        """
        try:
            # Información básica de la orden
            pair = config.get('pair', 'Unknown')
            order_type = order_info.get('side', 'Unknown').upper()
            amount = order_info.get('amount', 0)
            price = order_info.get('price', 0)
            total = amount * price
            
            # Icono según tipo de orden
            order_icon = "🟢" if order_type == "BUY" else "🔴"
            
            # Calcular P&L si tenemos exchange
            pnl_info = ""
            if exchange and config.get('total_capital'):
                balance = self.get_current_balance(exchange, pair)
                pnl_data = self.calculate_pnl_with_explanation(
                    balance, 
                    config['total_capital'], 
                    config.get('mode', 'UNKNOWN')
                )
                
                pnl_info = f"""
                <b>💰 P&L Actual:</b>
                Total: ${pnl_data['total_value']:.2f}
                P&L: {pnl_data['pnl_icon']} ${pnl_data['total_pnl']:.2f} ({pnl_data['total_pnl_percentage']:.2f}%)
                """.strip()
            
            message = f"""
            {order_icon} <b>Grid Trade Ejecutado</b>

            <b>📊 Orden:</b>
            Par: {pair}
            Tipo: {order_type}
            Cantidad: {amount:.6f}
            Precio: ${price:.2f}
            Total: ${total:.2f}

            {pnl_info}

            <b>⚙️ Config:</b> Grid {config.get('grid_levels', 'N/A')} niveles
            """.strip()
            
            self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de trade: {e}")

    def send_grid_hourly_summary(self, active_orders: List[dict], config: dict, trades_count: int, exchange: Optional[ccxt.Exchange] = None):
        """
        Envía resumen horario del grid bot.
        
        Args:
            active_orders: Lista de órdenes activas
            config: Configuración del bot
            trades_count: Número de trades ejecutados
            exchange: Instancia del exchange (opcional)
        """
        try:
            pair = config.get('pair', 'Unknown')
            
            # Información de órdenes activas
            buy_orders = len([o for o in active_orders if o.get('side') == 'buy'])
            sell_orders = len([o for o in active_orders if o.get('side') == 'sell'])
            
            # Calcular balance y P&L si tenemos exchange
            balance_info = ""
            if exchange and config.get('total_capital'):
                balance = self.get_current_balance(exchange, pair)
                pnl_data = self.calculate_pnl_with_explanation(
                    balance, 
                    config['total_capital'], 
                    config.get('mode', 'UNKNOWN')
                )
                
                balance_info = f"""
                <b>💰 Estado Financiero:</b>
                USDT: ${balance['usdt']:.2f}
                {balance['crypto_symbol']}: {balance['crypto']:.6f}
                Precio actual: ${balance['current_price']:.2f}
                Total: ${balance['total_value']:.2f}
                
                <b>📈 P&L:</b>
                P&L: {pnl_data['pnl_icon']} ${pnl_data['total_pnl']:.2f}
                Porcentaje: {pnl_data['total_pnl_percentage']:.2f}%
                """.strip()
            
            message = f"""
            📊 <b>Resumen Horario - Grid Bot</b>

            <b>🎯 Par:</b> {pair}
            <b>📋 Actividad:</b>
            Trades ejecutados: {trades_count}
            Órdenes activas: {len(active_orders)}
            └ Compra: {buy_orders} | Venta: {sell_orders}

            {balance_info}

            <b>⚙️ Configuración:</b>
            Niveles: {config.get('grid_levels', 'N/A')}
            Rango: {config.get('price_range_percent', 'N/A')}%
            Capital: ${config.get('total_capital', 0):.2f}
            """.strip()
            
            self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando resumen horario: {e}")


# Instancia global del servicio de trading
telegram_trading_service = TelegramTradingService() 