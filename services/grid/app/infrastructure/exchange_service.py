"""
Servicio de exchange para interactuar con Binance.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation, ConversionSyntax
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
                    'defaultType': 'spot',
                    'warnOnFetchOpenOrdersWithoutSymbol': False
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
            
            # Verificar valor mínimo específico del par
            order_value = price * amount
            min_order_value = self.get_minimum_order_value(pair)
            
            if order_value < min_order_value:
                raise ValueError(f"Valor de orden ${order_value:.2f} menor al mínimo ${min_order_value} para {pair}")
            
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
            
            logger.info(f"✅ Orden creada: {side} {amount} {pair} a ${price} (${order_value:.2f}) (ID: {order_result['id']})")
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
            
            # Valores mínimos conocidos para pares comunes (fallback)
            known_minimums = {
                'BTC/USDT': Decimal('10.0'),    # $10 mínimo
                'ETH/USDT': Decimal('10.0'),    # $10 mínimo
                'BNB/USDT': Decimal('10.0'),    # $10 mínimo
                'ADA/USDT': Decimal('10.0'),    # $10 mínimo
                'SOL/USDT': Decimal('10.0'),    # $10 mínimo
                'AVAX/USDT': Decimal('10.0'),   # $10 mínimo
                'DOT/USDT': Decimal('10.0'),    # $10 mínimo
                'LINK/USDT': Decimal('10.0'),   # $10 mínimo
                'MATIC/USDT': Decimal('10.0'),  # $10 mínimo
                'KMD/USDT': Decimal('10.0'),    # $10 mínimo
            }
            
            # Usar valor del exchange o fallback conocido
            if cost_min and cost_min > 0:
                min_value = Decimal(str(cost_min))
            else:
                min_value = known_minimums.get(pair, Decimal(MIN_ORDER_VALUE_USDT))
            
            logger.debug(f"💰 Valor mínimo {pair}: ${min_value}")
            return min_value
            
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
                try:
                    # Convertir id y symbol a str estándar
                    order_id = str(order['id'])
                    pair = str(order['symbol'])
                    self.exchange.cancel_order(order_id, pair)
                    count += 1
                    logger.debug(f"✅ Orden cancelada: {order_id} en {pair}")
                except Exception as order_error:
                    logger.warning(f"⚠️ Error cancelando orden {order.get('id', 'unknown')}: {order_error}")
                    continue
                    
            logger.info(f"✅ Canceladas {count} órdenes abiertas")
            return count
        except Exception as e:
            logger.error(f"❌ Error cancelando todas las órdenes: {e}")
            return 0

    def cancel_all_orders_for_pair(self, pair: str) -> int:
        """
        Cancela todas las órdenes abiertas para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            
        Returns:
            int: Número de órdenes canceladas
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            open_orders = self.exchange.fetch_open_orders()
            count = 0
            
            for order in open_orders:
                order_symbol = str(order['symbol'])
                if order_symbol == pair:
                    try:
                        order_id = str(order['id'])
                        self.exchange.cancel_order(order_id, pair)
                        count += 1
                        logger.debug(f"✅ Orden cancelada: {order_id} en {pair}")
                    except Exception as order_error:
                        logger.warning(f"⚠️ Error cancelando orden {order.get('id', 'unknown')} en {pair}: {order_error}")
                        continue
                    
            logger.info(f"✅ Canceladas {count} órdenes abiertas para {pair}")
            return count
        except Exception as e:
            logger.error(f"❌ Error cancelando órdenes para {pair}: {e}")
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
                
                try:
                    # Obtener precio de mercado para venta
                    ticker = self.exchange.fetch_ticker(pair)
                    price = Decimal(str(ticker['last']))
                    
                    # Calcular valor de la orden
                    order_value = free * price
                    
                    # Obtener valor mínimo requerido
                    min_order_value = self.get_minimum_order_value(pair)
                    
                    # Verificar si el valor es suficiente
                    if order_value < min_order_value:
                        logger.warning(f"⚠️ Posición {free} {currency} (${order_value:.2f}) menor al mínimo ${min_order_value} - Saltando")
                        continue
                    
                    # Crear orden de mercado para vender toda la posición
                    self.exchange.create_order(
                        symbol=pair, 
                        type='market', 
                        side='sell', 
                        amount=float(free)
                    )
                    
                    sold[currency] = free
                    logger.info(f"🧹 Vendida posición {free} {currency} por ~${order_value:.2f} USDT")
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # Manejar error NOTIONAL específicamente
                    if "NOTIONAL" in error_msg:
                        logger.warning(f"⚠️ Posición {free} {currency} muy pequeña para vender (error NOTIONAL) - Saltando")
                        continue
                    elif "Filter failure" in error_msg:
                        logger.warning(f"⚠️ Filtro de exchange rechazó venta de {free} {currency} - Saltando")
                        continue
                    else:
                        logger.error(f"❌ Error vendiendo {free} {currency}: {error_msg}")
                        continue
            
            return sold
            
        except Exception as e:
            logger.error(f"❌ Error vendiendo posiciones: {e}")
            return sold
    
    def sell_position_with_retry(self, currency: str, amount: Decimal, max_retries: int = 3) -> bool:
        """
        Intenta vender una posición con reintentos y manejo de errores específicos.
        
        Args:
            currency: Moneda a vender
            amount: Cantidad a vender
            max_retries: Número máximo de reintentos
            
        Returns:
            True si se vendió exitosamente
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            pair = f"{currency}/USDT"
            
            for attempt in range(max_retries):
                try:
                    # Obtener precio actual
                    ticker = self.exchange.fetch_ticker(pair)
                    price = Decimal(str(ticker['last']))
                    
                    # Calcular valor de la orden
                    order_value = amount * price
                    
                    # Obtener valor mínimo requerido
                    min_order_value = self.get_minimum_order_value(pair)
                    
                    # Verificar si el valor es suficiente
                    if order_value < min_order_value:
                        logger.warning(f"⚠️ Posición {amount} {currency} (${order_value:.2f}) menor al mínimo ${min_order_value}")
                        return False
                    
                    # Intentar vender
                    self.exchange.create_order(
                        symbol=pair,
                        type='market',
                        side='sell',
                        amount=float(amount)
                    )
                    
                    logger.info(f"✅ Vendida posición {amount} {currency} por ~${order_value:.2f} USDT")
                    return True
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    if "NOTIONAL" in error_msg or "Filter failure" in error_msg:
                        logger.warning(f"⚠️ Intento {attempt + 1}: Posición {amount} {currency} muy pequeña")
                        if attempt == max_retries - 1:
                            logger.warning(f"⚠️ No se pudo vender {amount} {currency} después de {max_retries} intentos")
                            return False
                        continue
                    else:
                        logger.error(f"❌ Error vendiendo {amount} {currency}: {error_msg}")
                        return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en sell_position_with_retry: {e}")
            return False
    
    def validate_order_after_fees(self, pair: str, side: str, amount: Decimal, price: Decimal) -> Dict[str, Any]:
        """
        Valida que una orden cumpla con el mínimo NOTIONAL después de las comisiones.
        
        Args:
            pair: Par de trading
            side: 'buy' o 'sell'
            amount: Cantidad de la orden
            price: Precio de la orden
            
        Returns:
            Dict con resultado de la validación
        """
        try:
            # Calcular valor bruto de la orden
            gross_value = amount * price
            
            # Obtener valor mínimo requerido
            min_order_value = self.get_minimum_order_value(pair)
            
            # Calcular cantidad neta después de comisiones
            net_amount = self.calculate_net_amount_after_fees(amount, price, side, pair)
            
            # Calcular valor neto después de comisiones
            if side == 'buy':
                # En compra: recibimos menos cantidad, pero el valor pagado es el mismo
                net_value = gross_value  # Pagamos el valor completo
            else:
                # En venta: recibimos menos USDT por las comisiones
                net_value = net_amount * price
            
            # Verificar si cumple con el mínimo
            meets_minimum = net_value >= min_order_value
            
            result = {
                'valid': meets_minimum,
                'gross_value': gross_value,
                'net_value': net_value,
                'min_required': min_order_value,
                'net_amount': net_amount,
                'fees_impact': gross_value - net_value,
                'margin': net_value - min_order_value if meets_minimum else min_order_value - net_value
            }
            
            if not meets_minimum:
                logger.warning(f"⚠️ Orden {side} {amount} {pair} a ${price} no cumple mínimo después de comisiones: ${net_value:.2f} < ${min_order_value}")
            else:
                logger.debug(f"✅ Orden {side} {amount} {pair} válida: ${net_value:.2f} >= ${min_order_value} (margen: ${result['margin']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error validando orden después de comisiones: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

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
        MEJORADO: Prioriza USDT para operaciones de compra, pero usa balance real para ventas.
        
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
            
            # MEJORA: Usar balance real de la moneda base para ventas
            # Para operaciones de venta, siempre usar el balance real disponible
            allocated_base_balance = total_base_balance
            
            # Para operaciones de compra, mantener la priorización de USDT
            if total_quote_balance >= allocated_capital:
                # Hay suficiente USDT, asignar todo el capital en USDT
                allocated_quote_balance = allocated_capital
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
                    
                    # Asignar proporcionalmente solo al USDT (base ya está asignado con balance real)
                    allocated_quote_balance = total_quote_balance * allocation_ratio
                    
                    logger.debug(f"🔒 Bot {pair}: Capital asignado ${allocated_capital:.2f} de ${total_value_usdt:.2f} total (ratio: {allocation_ratio:.3f})")
                    
                else:
                    # No hay suficiente balance, usar todo lo disponible
                    allocated_quote_balance = total_quote_balance
                    logger.warning(f"⚠️ Bot {pair}: Capital insuficiente. Asignado: ${allocated_capital:.2f}, Disponible: ${total_value_usdt:.2f}")
            
            # Calcular valores en USDT
            allocated_base_value_usdt = allocated_base_balance * current_price
            allocated_quote_value_usdt = allocated_quote_balance
            
            logger.debug(f"💰 Bot {pair}: Balance asignado - {base_currency}: {allocated_base_balance} (${allocated_base_value_usdt:.2f}), {quote_currency}: {allocated_quote_balance} (${allocated_quote_value_usdt:.2f})")
            
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

    def get_active_orders_from_exchange(self, pair: str) -> List[Dict[str, Any]]:
        """
        Obtiene las órdenes activas directamente del exchange para un par específico.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            
        Returns:
            Lista de órdenes activas con información completa del exchange
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            logger.debug(f"🔍 CONSULTANDO órdenes activas en exchange para {pair}")
            
            # Verificar modo de trading
            trading_mode = self.get_trading_mode()
            logger.debug(f"🔧 Modo de trading actual: {trading_mode}")
            
            # Obtener órdenes abiertas del exchange
            open_orders = self.exchange.fetch_open_orders(pair)
            
            logger.debug(f"📋 Raw open orders from exchange for {pair}: {len(open_orders)} orders")
            
            # Formatear órdenes para consistencia
            formatted_orders = []
            for order in open_orders:
                try:
                    formatted_order = {
                        'exchange_order_id': order['id'],
                        'pair': order['symbol'],
                        'side': order['side'],
                        'amount': Decimal(str(order['amount'])),
                        'price': Decimal(str(order['price'])),
                        'status': order['status'],
                        'filled': Decimal(str(order['filled'])),
                        'remaining': Decimal(str(order['remaining'])),
                        'timestamp': order['timestamp'],
                        'type': order['type']
                    }
                    formatted_orders.append(formatted_order)
                    logger.debug(f"   - Order {order['id']}: {order['side']} {order['amount']} @ {order['price']}")
                except Exception as order_error:
                    logger.warning(f"⚠️ Error formateando orden {order.get('id', 'unknown')}: {order_error}")
                    continue
            
            # Solo log INFO si no hay órdenes (caso importante)
            if not formatted_orders:
                logger.warning(f"⚠️ NO SE ENCONTRARON ÓRDENES ACTIVAS en exchange para {pair}")
                # Verificar si hay algún error específico
                try:
                    # Intentar obtener información del mercado para verificar que el par existe
                    market_info = self.exchange.market(pair)
                    logger.debug(f"✅ Mercado {pair} existe y es válido")
                except Exception as market_error:
                    logger.error(f"❌ Error verificando mercado {pair}: {market_error}")
            else:
                logger.debug(f"📋 Órdenes activas en exchange para {pair}: {len(formatted_orders)} órdenes formateadas")
            
            return formatted_orders
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo órdenes activas del exchange para {pair}: {e}")
            return []

    def get_real_balances_from_exchange(self, pair: str) -> Dict[str, Any]:
        """
        Obtiene los balances reales directamente del exchange para un par específico.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            
        Returns:
            Dict con balances reales de ambas monedas del par
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            base_currency, quote_currency = pair.split('/')
            
            # Obtener balances reales del exchange
            balances = self.exchange.fetch_balance()
            
            # Extraer balances libres (disponibles para trading)
            base_balance = Decimal(str(balances.get(base_currency, {}).get('free', 0)))
            quote_balance = Decimal(str(balances.get(quote_currency, {}).get('free', 0)))
            
            # Obtener precio actual para conversión a USDT
            current_price = self.get_current_price(pair)
            base_value_usdt = base_balance * current_price
            
            logger.debug(f"💰 Balances reales {pair}: {base_balance} {base_currency} (${base_value_usdt:.2f}) + {quote_balance} {quote_currency}")
            
            return {
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'base_balance': base_balance,
                'quote_balance': quote_balance,
                'base_value_usdt': base_value_usdt,
                'quote_value_usdt': quote_balance,  # Asumimos que quote es USDT
                'total_value_usdt': base_value_usdt + quote_balance
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balances reales del exchange para {pair}: {e}")
            base_currency = pair.split('/')[0] if '/' in pair else 'UNKNOWN'
            quote_currency = pair.split('/')[1] if '/' in pair else 'UNKNOWN'
            return {
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'base_balance': Decimal('0'),
                'quote_balance': Decimal('0'),
                'base_value_usdt': Decimal('0'),
                'quote_value_usdt': Decimal('0'),
                'total_value_usdt': Decimal('0')
            } 

    def get_filled_orders_from_exchange(self, pair: str, since_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene órdenes completadas (fills) directamente del exchange.
        Usa fetch_closed_orders para detectar fills de manera eficiente.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            since_timestamp: Timestamp desde cuando buscar (opcional)
            
        Returns:
            Lista de órdenes completadas con información completa
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Obtener órdenes cerradas recientemente del exchange
            closed_orders = self.exchange.fetch_closed_orders(
                symbol=pair,
                since=since_timestamp,
                limit=100  # Limitar para eficiencia
            )
            
            # Función auxiliar para convertir valores a Decimal de forma segura
            def safe_decimal(value, default=Decimal('0')):
                """Convierte un valor a Decimal de forma segura."""
                try:
                    if value is None:
                        return default
                    if isinstance(value, (int, float)):
                        return Decimal(str(value))
                    if isinstance(value, str):
                        # Limpiar string de caracteres no numéricos
                        cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
                        if cleaned:
                            return Decimal(cleaned)
                        return default
                    return Decimal(str(value))
                except (ValueError, TypeError, InvalidOperation, ConversionSyntax):
                    logger.warning(f"⚠️ Error convirtiendo valor a Decimal: {value} (tipo: {type(value)})")
                    return default
            
            # Filtrar solo órdenes completadas (filled)
            filled_orders = []
            for order in closed_orders:
                try:
                    # Verificar si la orden está completada
                    filled_amount = order.get('filled', 0)
                    if order.get('status') == 'closed' and filled_amount and float(filled_amount) > 0:
                        formatted_order = {
                            'exchange_order_id': str(order.get('id', '')),
                            'pair': str(order.get('symbol', '')),
                            'side': str(order.get('side', '')),
                            'amount': safe_decimal(order.get('amount')),
                            'price': safe_decimal(order.get('price')),
                            'status': str(order.get('status', '')),
                            'filled': safe_decimal(order.get('filled')),
                            'remaining': safe_decimal(order.get('remaining')),
                            'timestamp': int(order.get('timestamp', 0) or 0),
                            'type': str(order.get('type', '')),
                            'cost': safe_decimal(order.get('cost')),
                            'average': safe_decimal(order.get('average'))
                        }
                        filled_orders.append(formatted_order)
                except Exception as order_error:
                    logger.warning(f"⚠️ Error procesando orden en {pair}: {order_error}")
                    continue
            
            logger.debug(f"💰 Órdenes completadas en exchange para {pair}: {len(filled_orders)} fills")
            return filled_orders
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo órdenes completadas del exchange para {pair}: {e}")
            return []

    def get_order_status_from_exchange(self, pair: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de una orden específica del exchange.
        Usa fetch_order para verificación precisa de estado.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            order_id: ID de la orden en el exchange
            
        Returns:
            Dict con información completa de la orden o None si no existe
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Obtener estado actual de la orden
            order = self.exchange.fetch_order(order_id, pair)
            
            if order:
                # Función auxiliar para convertir valores a Decimal de forma segura
                def safe_decimal(value, default=Decimal('0')):
                    """Convierte un valor a Decimal de forma segura."""
                    try:
                        if value is None:
                            return default
                        if isinstance(value, (int, float)):
                            return Decimal(str(value))
                        if isinstance(value, str):
                            # Limpiar string de caracteres no numéricos
                            cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
                            if cleaned:
                                return Decimal(cleaned)
                            return default
                        return Decimal(str(value))
                    except (ValueError, TypeError, InvalidOperation, ConversionSyntax):
                        logger.warning(f"⚠️ Error convirtiendo valor a Decimal: {value} (tipo: {type(value)})")
                        return default
                
                formatted_order = {
                    'exchange_order_id': str(order.get('id', '')),
                    'pair': str(order.get('symbol', '')),
                    'side': str(order.get('side', '')),
                    'amount': safe_decimal(order.get('amount')),
                    'price': safe_decimal(order.get('price')),
                    'status': str(order.get('status', '')),
                    'filled': safe_decimal(order.get('filled')),
                    'remaining': safe_decimal(order.get('remaining')),
                    'timestamp': int(order.get('timestamp', 0) or 0),
                    'type': str(order.get('type', '')),
                    'cost': safe_decimal(order.get('cost')),
                    'average': safe_decimal(order.get('average'))
                }
                
                logger.debug(f"📋 Estado de orden {order_id} en {pair}: {order.get('status', 'unknown')} (filled: {order.get('filled', 0)})")
                return formatted_order
            else:
                logger.warning(f"⚠️ Orden {order_id} no encontrada en {pair}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de orden {order_id} en {pair}: {e}")
            return None

    def get_recent_trades_from_exchange(self, pair: str, since_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene trades recientes ejecutados directamente del exchange.
        Usa fetch_my_trades para obtener información detallada de trades.
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            since_timestamp: Timestamp desde cuando buscar (opcional)
            
        Returns:
            Lista de trades ejecutados con información completa
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Obtener trades recientes del exchange
            trades = self.exchange.fetch_my_trades(
                symbol=pair,
                since=since_timestamp,
                limit=50  # Limitar para eficiencia
            )
            
            # Formatear trades para consistencia
            formatted_trades = []
            for trade in trades:
                try:
                    # Usar getattr para acceder a los campos de manera segura
                    trade_id = str(getattr(trade, 'id', ''))
                    order_id = str(getattr(trade, 'order', ''))
                    trade_pair = str(getattr(trade, 'symbol', ''))
                    side = str(getattr(trade, 'side', ''))
                    amount = Decimal(str(getattr(trade, 'amount', 0)))
                    price = Decimal(str(getattr(trade, 'price', 0)))
                    cost = Decimal(str(getattr(trade, 'cost', 0)))
                    
                    # Manejar fee de manera segura
                    fee_obj = getattr(trade, 'fee', {})
                    fee_cost = getattr(fee_obj, 'cost', 0) if fee_obj else 0
                    fee = Decimal(str(fee_cost))
                    
                    timestamp = int(getattr(trade, 'timestamp', 0) or 0)
                    datetime_str = str(getattr(trade, 'datetime', ''))
                    
                    formatted_trade = {
                        'trade_id': trade_id,
                        'order_id': order_id,
                        'pair': trade_pair,
                        'side': side,
                        'amount': amount,
                        'price': price,
                        'cost': cost,
                        'fee': fee,
                        'timestamp': timestamp,
                        'datetime': datetime_str
                    }
                    formatted_trades.append(formatted_trade)
                except Exception as trade_error:
                    logger.warning(f"⚠️ Error procesando trade en {pair}: {trade_error}")
                    continue
            
            logger.debug(f"💱 Trades recientes en exchange para {pair}: {len(formatted_trades)} trades")
            return formatted_trades
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo trades recientes del exchange para {pair}: {e}")
            return []

    def detect_fills_by_comparison(self, pair: str, previous_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detecta fills comparando órdenes activas anteriores con las actuales.
        Método eficaz para detectar órdenes que desaparecieron (se completaron).
        
        Args:
            pair: Par de trading (ej: 'BTC/USDT')
            previous_orders: Lista de órdenes activas del ciclo anterior
            
        Returns:
            Lista de órdenes que se completaron (fills detectados)
        """
        try:
            if not self.exchange:
                raise Exception("Exchange no inicializado")
            
            # Obtener órdenes activas actuales
            current_orders = self.get_active_orders_from_exchange(pair)
            
            # Crear sets de IDs para comparación eficiente
            previous_ids = {order['exchange_order_id'] for order in previous_orders}
            current_ids = {order['exchange_order_id'] for order in current_orders}
            
            # Órdenes que desaparecieron (potenciales fills)
            disappeared_ids = previous_ids - current_ids
            
            if not disappeared_ids:
                return []
            
            # Verificar estado de órdenes desaparecidas
            fills_detected = []
            for order_id in disappeared_ids:
                order_status = self.get_order_status_from_exchange(pair, order_id)
                if order_status and order_status['status'] == 'closed' and order_status['filled'] > 0:
                    logger.info(f"💰 Fill detectado por comparación: {order_id} en {pair}")
                    fills_detected.append(order_status)
                else:
                    logger.debug(f"ℹ️ Orden {order_id} desapareció pero no está completada")
            
            logger.info(f"🔍 Detección por comparación: {len(fills_detected)} fills de {len(disappeared_ids)} órdenes desaparecidas")
            return fills_detected
            
        except Exception as e:
            logger.error(f"❌ Error en detección de fills por comparación para {pair}: {e}")
            return [] 