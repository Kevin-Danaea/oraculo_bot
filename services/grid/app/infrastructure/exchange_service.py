"""
Servicio de exchange para interactuar con Binance.
"""
from typing import Dict, Any
from decimal import Decimal
import ccxt
import uuid

from app.domain.interfaces import ExchangeService
from app.domain.entities import GridOrder, GridConfig
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
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Configurar modo sandbox explícitamente
            if sandbox:
                self.exchange.set_sandbox_mode(True)
                logger.info("🧪 Modo SANDBOX activado para Binance")
            else:
                self.exchange.set_sandbox_mode(False)
                logger.info("🚀 Modo PRODUCCIÓN activado para Binance")
            
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
            if self.exchange:
                self.exchange.set_sandbox_mode(True)
            logger.info("🧪 Cambiado a modo SANDBOX y activado set_sandbox_mode(True)")
        except Exception as e:
            logger.error(f"❌ Error cambiando a sandbox: {e}")

    def switch_to_production(self):
        """Cambia el exchange a modo producción y actualiza credenciales."""
        try:
            self.mode = 'production'
            self._initialize_exchange()
            if self.exchange:
                self.exchange.set_sandbox_mode(False)
            logger.info("🚀 Cambiado a modo PRODUCCIÓN y activado set_sandbox_mode(False)")
        except Exception as e:
            logger.error(f"❌ Error cambiando a producción: {e}")

    def get_trading_mode(self) -> str:
        """Obtiene el modo de trading actual."""
        if not self.exchange:
            return "disconnected"
        # Verificar el modo sandbox configurado
        return "sandbox" if self.mode == 'sandbox' else "production"

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

    def get_trading_fees(self, pair: str) -> Dict[str, Decimal]:
        """Obtiene las comisiones de trading para un par."""
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Obtener información del mercado
            markets = self.exchange.load_markets()
            market_info = markets.get(pair, {})
            
            # Obtener comisiones (maker y taker)
            maker_fee = Decimal(str(market_info.get('maker', 0.001)))  # 0.1% por defecto
            taker_fee = Decimal(str(market_info.get('taker', 0.001)))  # 0.1% por defecto
            
            logger.debug(f"💰 Comisiones {pair}: Maker {maker_fee*100:.3f}%, Taker {taker_fee*100:.3f}%")
            
            return {
                'maker': maker_fee,
                'taker': taker_fee
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo comisiones para {pair}: {e}")
            return {
                'maker': Decimal('0.001'),  # 0.1% por defecto
                'taker': Decimal('0.001')   # 0.1% por defecto
            }

    def calculate_net_amount_after_fees(self, gross_amount: Decimal, price: Decimal, side: str, pair: str) -> Decimal:
        """
        Calcula la cantidad neta que se recibirá después de comisiones.
        
        Args:
            gross_amount: Cantidad bruta de la orden
            price: Precio de la orden
            side: 'buy' o 'sell'
            pair: Par de trading
            
        Returns:
            Cantidad neta después de comisiones
        """
        try:
            fees = self.get_trading_fees(pair)
            
            # Para órdenes limit usamos maker fee, para market usamos taker fee
            fee_rate = fees['maker']  # Asumimos limit orders por defecto
            
            if side == 'buy':
                # En compra: recibimos menos de la moneda base por las comisiones
                # Ejemplo: Compramos 1 ETH, pero recibimos 0.999 ETH
                net_amount = gross_amount * (Decimal('1') - fee_rate)
            else:
                # En venta: recibimos menos USDT por las comisiones
                # Ejemplo: Vendemos 1 ETH a $2000, pero recibimos $1998 USDT
                gross_value = gross_amount * price
                net_value = gross_value * (Decimal('1') - fee_rate)
                net_amount = net_value / price  # Convertir de vuelta a cantidad
            
            logger.debug(f"💰 Cantidad neta después de comisiones {side}: {gross_amount} → {net_amount}")
            return net_amount.quantize(Decimal('0.000001'))
            
        except Exception as e:
            logger.error(f"❌ Error calculando cantidad neta: {e}")
            return gross_amount * Decimal('0.999')  # Fallback: 0.1% de comisión

    def get_total_balance_in_usdt(self, pair: str) -> Dict[str, Decimal]:
        """
        Obtiene el balance total convertido a USDT para un par específico.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            
        Returns:
            Dict con balances en USDT de ambas monedas del par
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            base_currency, quote_currency = pair.split('/')
            
            # Obtener balances
            balances = self.exchange.fetch_balance()
            base_balance = Decimal(str(balances.get(base_currency, {}).get('free', 0)))
            quote_balance = Decimal(str(balances.get(quote_currency, {}).get('free', 0)))
            
            # Obtener precio actual
            current_price = self.get_current_price(pair)
            
            # Convertir balance base a USDT
            base_value_usdt = base_balance * current_price
            
            # El quote ya está en USDT (asumimos que siempre es USDT)
            quote_value_usdt = quote_balance
            
            total_value_usdt = base_value_usdt + quote_value_usdt
            
            logger.debug(f"💰 Balance total {pair}: {base_balance} {base_currency} (${base_value_usdt:.2f}) + {quote_balance} {quote_currency} = ${total_value_usdt:.2f}")
            
            return {
                'base_balance': base_balance,
                'quote_balance': quote_balance,
                'base_value_usdt': base_value_usdt,
                'quote_value_usdt': quote_value_usdt,
                'total_value_usdt': total_value_usdt
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance total: {e}")
            return {
                'base_balance': Decimal('0'),
                'quote_balance': Decimal('0'),
                'base_value_usdt': Decimal('0'),
                'quote_value_usdt': Decimal('0'),
                'total_value_usdt': Decimal('0')
            }

    def get_bot_allocated_balance(self, config: GridConfig) -> Dict[str, Decimal]:
        """
        Obtiene el balance asignado específicamente para un bot, respetando el aislamiento de capital.
        MEJORADO: Prioriza USDT para operaciones de compra.
        
        Args:
            config: Configuración del bot con capital asignado
            
        Returns:
            Dict con balances asignados al bot específico
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            pair = config.pair
            allocated_capital = Decimal(config.total_capital)
            base_currency, quote_currency = pair.split('/')
            
            # Obtener balances totales de la cuenta
            balances = self.exchange.fetch_balance()
            total_base_balance = Decimal(str(balances.get(base_currency, {}).get('free', 0)))
            total_quote_balance = Decimal(str(balances.get(quote_currency, {}).get('free', 0)))
            
            # Obtener precio actual
            current_price = self.get_current_price(pair)
            
            # MEJORA: Priorizar USDT para operaciones de compra
            # Si hay suficiente USDT disponible, asignar más USDT al bot
            if total_quote_balance >= allocated_capital:
                # Hay suficiente USDT, asignar todo el capital en USDT
                allocated_quote_balance = allocated_capital
                allocated_base_balance = Decimal('0')
                logger.debug(f"🔒 Bot {pair}: Capital asignado ${allocated_capital:.2f} en USDT puro")
                
            else:
                # No hay suficiente USDT, usar distribución proporcional
                total_value_usdt = total_base_balance * current_price + total_quote_balance
                
                if total_value_usdt >= allocated_capital:
                    # Hay suficiente balance total, calcular proporción
                    if total_value_usdt > 0:
                        allocation_ratio = allocated_capital / total_value_usdt
                    else:
                        allocation_ratio = Decimal('0')
                    
                    # Asignar proporcionalmente
                    allocated_base_balance = total_base_balance * allocation_ratio
                    allocated_quote_balance = total_quote_balance * allocation_ratio
                    
                    logger.debug(f"🔒 Bot {pair}: Capital asignado ${allocated_capital:.2f} de ${total_value_usdt:.2f} total (ratio: {allocation_ratio:.3f})")
                    
                else:
                    # No hay suficiente balance, usar todo lo disponible
                    allocated_base_balance = total_base_balance
                    allocated_quote_balance = total_quote_balance
                    logger.warning(f"⚠️ Bot {pair}: Capital insuficiente. Asignado: ${allocated_capital:.2f}, Disponible: ${total_value_usdt:.2f}")
            
            # Calcular valores en USDT
            allocated_base_value_usdt = allocated_base_balance * current_price
            allocated_quote_value_usdt = allocated_quote_balance
            
            return {
                'allocated_capital': allocated_capital,
                'base_balance': allocated_base_balance,
                'quote_balance': allocated_quote_balance,
                'base_value_usdt': allocated_base_value_usdt,
                'quote_value_usdt': allocated_quote_value_usdt,
                'total_value_usdt': allocated_base_value_usdt + allocated_quote_value_usdt,
                'total_available_in_account': total_base_balance * current_price + total_quote_balance
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance asignado para bot {config.pair}: {e}")
            return {
                'allocated_capital': Decimal('0'),
                'base_balance': Decimal('0'),
                'quote_balance': Decimal('0'),
                'base_value_usdt': Decimal('0'),
                'quote_value_usdt': Decimal('0'),
                'total_value_usdt': Decimal('0'),
                'total_available_in_account': Decimal('0')
            }

    def can_bot_use_capital(self, config: GridConfig, required_amount: Decimal, side: str) -> Dict[str, Any]:
        """
        Verifica si un bot puede usar una cantidad específica de capital sin exceder su asignación.
        
        Args:
            config: Configuración del bot
            required_amount: Cantidad requerida
            side: 'buy' (necesita USDT) o 'sell' (necesita base currency)
            
        Returns:
            Dict con información de viabilidad
        """
        try:
            bot_balance = self.get_bot_allocated_balance(config)
            pair = config.pair
            base_currency = pair.split('/')[0]
            
            if side == 'buy':
                # Para compra necesitamos USDT
                available_balance = bot_balance['quote_balance']
                currency_needed = 'USDT'
                required_usdt = required_amount
            else:
                # Para venta necesitamos la moneda base
                available_balance = bot_balance['base_balance']
                currency_needed = base_currency
                required_usdt = required_amount * self.get_current_price(pair)
            
            can_use = available_balance >= required_amount
            remaining_after_use = available_balance - required_amount if can_use else available_balance
            
            result = {
                'can_use': can_use,
                'bot_pair': pair,
                'allocated_capital': bot_balance['allocated_capital'],
                'required_amount': required_amount,
                'required_usdt': required_usdt,
                'available_balance': available_balance,
                'currency_needed': currency_needed,
                'remaining_after_use': remaining_after_use,
                'total_bot_value': bot_balance['total_value_usdt']
            }
            
            if not can_use:
                logger.warning(f"🚫 Bot {pair} no puede usar {required_amount} {currency_needed}. Disponible: {available_balance}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error verificando uso de capital para bot {config.pair}: {e}")
            return {
                'can_use': False,
                'bot_pair': config.pair,
                'allocated_capital': Decimal('0'),
                'required_amount': required_amount,
                'required_usdt': Decimal('0'),
                'available_balance': Decimal('0'),
                'currency_needed': 'UNKNOWN',
                'remaining_after_use': Decimal('0'),
                'total_bot_value': Decimal('0')
            } 