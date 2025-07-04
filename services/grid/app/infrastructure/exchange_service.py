"""
Servicio de exchange para interactuar con Binance.
"""
from typing import Dict, Any
from decimal import Decimal
import ccxt
import uuid

from app.domain.interfaces import ExchangeService
from app.domain.entities import GridOrder
from app.config import MIN_ORDER_VALUE_USDT, EXCHANGE_NAME
from shared.config.settings import settings
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class BinanceExchangeService(ExchangeService):
    """Implementación del servicio de exchange usando Binance."""

    def __init__(self):
        """Inicializa la conexión con Binance."""
        # Modo actual: 'sandbox' o 'production'
        self.mode = getattr(settings, 'TRADING_MODE', 'sandbox')
        self.exchange = None
        self._initialize_exchange()
        logger.info(f"✅ BinanceExchangeService inicializado en modo {self.mode.upper()}.")

    def _initialize_exchange(self):
        """Inicializa la conexión con el exchange según self.mode."""
        try:
            sandbox = self.mode == 'sandbox'
            # Seleccionar credenciales según modo
            api_key = settings.PAPER_TRADING_API_KEY if sandbox else settings.BINANCE_API_KEY
            secret = settings.PAPER_TRADING_SECRET_KEY if sandbox else settings.BINANCE_API_SECRET
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret,
                'sandbox': sandbox,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            mode_str = "SANDBOX" if sandbox else "PRODUCCIÓN"
            logger.info(f"🔗 Conectado a Binance en modo {mode_str} con {'PAPER' if sandbox else 'PRODUCTION'} keys")
        except Exception as e:
            logger.error(f"❌ Error inicializando exchange: {e}")
            self.exchange = None

    def get_current_price(self, pair: str) -> Decimal:
        """Obtiene el precio actual de un par."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            ticker = self.exchange.fetch_ticker(pair)
            price = Decimal(str(ticker['last']))
            
            logger.debug(f"💰 Precio actual {pair}: ${price}")
            return price
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de {pair}: {e}")
            raise

    def get_balance(self, currency: str) -> Decimal:
        """Obtiene el balance de una moneda."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            balance = self.exchange.fetch_balance()
            free_balance = balance.get(currency, {}).get('free', 0)
            
            result = Decimal(str(free_balance))
            logger.debug(f"💳 Balance {currency}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance de {currency}: {e}")
            return Decimal('0')

    def create_order(self, pair: str, side: str, amount: Decimal, price: Decimal, order_type: str = 'limit') -> GridOrder:
        """Crea una orden en el exchange."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Verificar valor mínimo
            order_value = price * amount
            if order_value < Decimal(MIN_ORDER_VALUE_USDT):
                raise ValueError(f"Valor de orden ${order_value} menor al mínimo ${MIN_ORDER_VALUE_USDT}")
            
            # Crear orden en el exchange
            order_result = self.exchange.create_order(
                symbol=pair,
                type=order_type,  # type: ignore
                side=side,  # type: ignore
                amount=float(amount),
                price=float(price)
            )
            
            # Crear entidad GridOrder
            grid_order = GridOrder(
                id=str(uuid.uuid4()),
                exchange_order_id=order_result['id'],
                pair=pair,
                side=side,
                amount=amount,
                price=price,
                status='open',
                order_type='grid_buy' if side == 'buy' else 'grid_sell',
                grid_level=None,
                created_at=None,
                filled_at=None
            )
            
            logger.info(f"✅ Orden creada: {side} {amount} {pair} a ${price} (ID: {order_result['id']})")
            return grid_order
            
        except Exception as e:
            logger.error(f"❌ Error creando orden {side} {amount} {pair} a ${price}: {e}")
            raise

    def cancel_order(self, pair: str, order_id: str) -> bool:
        """Cancela una orden en el exchange."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            self.exchange.cancel_order(order_id, pair)
            logger.info(f"✅ Orden cancelada: {order_id} en {pair}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cancelando orden {order_id}: {e}")
            return False

    def get_order_status(self, pair: str, order_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una orden en el exchange."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            order = self.exchange.fetch_order(order_id, pair)
            
            return {
                'id': order['id'],
                'status': order['status'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de orden {order_id}: {e}")
            return {'status': 'unknown', 'error': str(e)}

    def get_minimum_order_value(self, pair: str) -> Decimal:
        """Obtiene el valor mínimo de orden para un par."""
        try:
            if not self.exchange:
                return Decimal(MIN_ORDER_VALUE_USDT)
            
            # Obtener información del mercado
            markets = self.exchange.load_markets()
            market_info = markets.get(pair, {})
            
            # Obtener límites mínimos
            limits = market_info.get('limits', {})
            cost_min = limits.get('cost', {}).get('min', MIN_ORDER_VALUE_USDT)
            
            return Decimal(str(cost_min))
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo valor mínimo para {pair}: {e}")
            return Decimal(MIN_ORDER_VALUE_USDT)

    def switch_to_sandbox(self):
        """Cambia el exchange a modo sandbox y actualiza credenciales."""
        try:
            self.mode = 'sandbox'
            self._initialize_exchange()
            logger.info("🧪 Cambiado a modo SANDBOX y actualizadas credenciales Paper Trading")
        except Exception as e:
            logger.error(f"❌ Error cambiando a sandbox: {e}")

    def switch_to_production(self):
        """Cambia el exchange a modo producción y actualiza credenciales."""
        try:
            self.mode = 'production'
            self._initialize_exchange()
            logger.info("🚀 Cambiado a modo PRODUCCIÓN y actualizadas credenciales de producción")
        except Exception as e:
            logger.error(f"❌ Error cambiando a producción: {e}")

    def get_trading_mode(self) -> str:
        """Obtiene el modo de trading actual."""
        if not self.exchange:
            return "disconnected"
        return "sandbox" if getattr(self.exchange, 'sandbox', False) else "production"

    def cancel_all_orders(self) -> int:
        """Cancela todas las órdenes abiertas en el exchange. Retorna el número de órdenes canceladas."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            open_orders = self.exchange.fetch_open_orders()
            count = 0
            for order in open_orders:
                # Convertir id y symbol a str estándar
                order_id = str(order['id'])
                pair = str(order['symbol'])
                self.exchange.cancel_order(order_id, pair)
                count += 1
            logger.info(f"✅ Canceladas {count} órdenes abiertas")
            return count
        except Exception as e:
            logger.error(f"❌ Error cancelando todas las órdenes: {e}")
            return 0

    def sell_all_positions(self) -> Dict[str, Decimal]:
        """Vende todas las posiciones abiertas en el exchange. Retorna un dict con montos vendidos por moneda."""
        sold = {}
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            balances = self.exchange.fetch_balance()
            for currency, info in balances.items():
                free = Decimal(str(info.get('free', 0)))
                # Solo liquidar posiciones distintas a USDT y mayor a cero
                if currency == 'USDT' or free <= 0:
                    continue
                pair = f"{currency}/USDT"
                # Obtener precio de mercado para venta
                ticker = self.exchange.fetch_ticker(pair)
                price = Decimal(str(ticker['last']))
                # Crear orden de mercado para vender toda la posición
                self.exchange.create_order(symbol=pair, type='market', side='sell', amount=float(free))
                sold[currency] = free
                logger.info(f"🧹 Vendida posición {free} {currency} en mercado ({pair})")
            return sold
        except Exception as e:
            logger.error(f"❌ Error vendiendo posiciones: {e}")
            return sold 