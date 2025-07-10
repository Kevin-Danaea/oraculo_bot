"""Exchange service implementation using CCXT."""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
import ccxt

from ..domain.entities import TradingResult
from ..domain.interfaces import IExchangeService
from ..config import get_config

logger = logging.getLogger(__name__)


class ExchangeService(IExchangeService):
    """Implementación del servicio de exchange usando CCXT."""
    
    def __init__(self):
        self.config = get_config()
        self.exchange = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """Asegura que el cliente esté inicializado."""
        if not self._initialized:
            self._initialize()
    
    def _initialize(self):
        """Inicializa la conexión con el exchange."""
        try:
            sandbox = True #self.config.binance_testnet
            
            # Seleccionar credenciales según modo
            api_key = self.config.paper_trading_api_key if sandbox else self.config.binance_api_key
            secret = self.config.paper_trading_secret_key if sandbox else self.config.binance_api_secret
            
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
            
            # Cargar mercados
            self.exchange.load_markets()
            
            self._initialized = True
            mode_str = "SANDBOX" if sandbox else "PRODUCCIÓN"
            logger.info(f"✅ Cliente CCXT inicializado exitosamente en modo {mode_str} con {'PAPER' if sandbox else 'PRODUCTION'} keys")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente CCXT: {str(e)}")
            raise
    
    def close(self):
        """Cierra la conexión con el cliente."""
        self._initialized = False
    
    def get_current_price(self, symbol: str) -> Decimal:
        """Obtiene el precio actual de un símbolo."""
        self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = Decimal(str(ticker['last']))
            logger.debug(f"Precio actual de {symbol}: {price}")
            return price
            
        except Exception as e:
            logger.error(f"Error obteniendo precio: {str(e)}")
            raise
    
    def get_balance(self, asset: str) -> Decimal:
        """Obtiene el balance de un activo."""
        self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            balance = self.exchange.fetch_balance()
            
            if asset in balance:
                free_balance = Decimal(str(balance[asset]['free']))
                logger.debug(f"Balance de {asset}: {free_balance}")
                return free_balance
            
            logger.warning(f"No se encontró balance para {asset}")
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Error obteniendo balance: {str(e)}")
            raise
    
    def place_market_buy_order(
        self, 
        symbol: str, 
        quantity: Decimal
    ) -> TradingResult:
        """Coloca una orden de compra a mercado."""
        self._ensure_initialized()
        
        if not self.exchange:
            return TradingResult(
                success=False,
                error_message="Exchange no inicializado"
            )
        
        try:
            logger.info(f"Ejecutando orden de compra: {quantity} {symbol}")
            
            order = self.exchange.create_market_buy_order(
                symbol, 
                float(quantity)
            )
            
            # Calcular comisiones
            fees = self._calculate_fees(symbol, quantity)
            
            logger.info(
                f"✅ Orden de compra ejecutada: {symbol} {quantity} - "
                f"Order ID: {order['id']}"
            )
            
            return TradingResult(
                success=True,
                order_id=order['id'],
                executed_price=Decimal(str(order['price'])) if order.get('price') else None,
                executed_quantity=Decimal(str(order['amount'])),
                fees=fees
            )
            
        except Exception as e:
            logger.error(f"❌ Error colocando orden de compra: {str(e)}")
            return TradingResult(
                success=False,
                error_message=str(e)
            )
    
    def place_market_sell_order(
        self, 
        symbol: str, 
        quantity: Decimal
    ) -> TradingResult:
        """Coloca una orden de venta a mercado."""
        self._ensure_initialized()
        
        if not self.exchange:
            return TradingResult(
                success=False,
                error_message="Exchange no inicializado"
            )
        
        try:
            logger.info(f"Ejecutando orden de venta: {quantity} {symbol}")
            
            order = self.exchange.create_market_sell_order(
                symbol, 
                float(quantity)
            )
            
            # Calcular comisiones
            fees = self._calculate_fees(symbol, quantity)
            
            logger.info(
                f"✅ Orden de venta ejecutada: {symbol} {quantity} - "
                f"Order ID: {order['id']}"
            )
            
            return TradingResult(
                success=True,
                order_id=order['id'],
                executed_price=Decimal(str(order['price'])) if order.get('price') else None,
                executed_quantity=Decimal(str(order['amount'])),
                fees=fees
            )
            
        except Exception as e:
            logger.error(f"❌ Error colocando orden de venta: {str(e)}")
            return TradingResult(
                success=False,
                error_message=str(e)
            )
    
    def _calculate_fees(self, symbol: str, quantity: Decimal) -> Decimal:
        """Calcula las comisiones para una operación."""
        try:
            # Obtener información de comisiones del mercado
            if self.exchange and hasattr(self.exchange, 'markets'):
                markets = self.exchange.markets
                if markets and symbol in markets:
                    market = markets[symbol]
                    maker_fee = market.get('maker', 0.001)  # Default 0.1%
                    
                    # Calcular comisión (simplificado)
                    fee_amount = quantity * Decimal(str(maker_fee))
                    logger.debug(f"Comisión calculada para {symbol}: {fee_amount}")
                    return fee_amount
            
            # Comisión por defecto
            default_fee = Decimal('0.001')  # 0.1%
            logger.warning(
                f"No se encontró comisión para {symbol}, usando default: {default_fee}"
            )
            return quantity * default_fee
            
        except Exception as e:
            logger.error(f"Error calculando comisiones: {str(e)}")
            return Decimal('0') 