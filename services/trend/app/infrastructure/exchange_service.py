"""Exchange service implementation using CCXT."""

import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
import asyncio

try:
    import ccxt.pro as ccxt  # type: ignore
    CCXT_AVAILABLE = True
except ImportError:
    try:
        import ccxt  # type: ignore
        CCXT_AVAILABLE = True
    except ImportError:
        # Las dependencias se instalarán cuando se despliegue el servicio
        ccxt = None
        CCXT_AVAILABLE = False

from ..domain.interfaces import IExchangeService
from ..config import get_config

logger = logging.getLogger(__name__)


class ExchangeService(IExchangeService):
    """Implementación del servicio de exchange usando CCXT."""
    
    def __init__(self):
        self.config = get_config()
        self.exchange: Optional[Any] = None
        self._initialized = False
        
    async def _ensure_initialized(self):
        """Asegura que el cliente esté inicializado."""
        if not self._initialized:
            await self._initialize()
    
    async def _initialize(self):
        """Inicializa el cliente de CCXT."""
        if not CCXT_AVAILABLE:
            raise RuntimeError("CCXT no está instalado")
            
        try:
            # Configurar exchange (Binance por defecto)
            exchange_config = {
                'apiKey': self.config.binance_api_key,
                'secret': self.config.binance_api_secret,
                'sandbox': self.config.binance_testnet,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # spot trading
                }
            }
            
            self.exchange = ccxt.binance(exchange_config)  # type: ignore
            
            # Cargar mercados
            await self.exchange.load_markets()
            
            self._initialized = True
            logger.info("Cliente CCXT inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando cliente CCXT: {str(e)}")
            raise
    
    async def close(self):
        """Cierra la conexión con el cliente."""
        if self.exchange:
            await self.exchange.close()
            self._initialized = False
    
    async def get_balance(self, asset: str) -> Decimal:
        """Obtiene el balance de un activo."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            balance = await self.exchange.fetch_balance()
            
            if asset in balance:
                free_balance = Decimal(str(balance[asset]['free']))
                logger.debug(f"Balance de {asset}: {free_balance}")
                return free_balance
            
            logger.warning(f"No se encontró balance para {asset}")
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Error obteniendo balance: {str(e)}")
            raise
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """Obtiene el precio actual de un símbolo."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            price = Decimal(str(ticker['last']))
            logger.debug(f"Precio actual de {symbol}: {price}")
            return price
            
        except Exception as e:
            logger.error(f"Error obteniendo precio: {str(e)}")
            raise
    
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal
    ) -> Dict[str, Any]:
        """Coloca una orden de mercado."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            order = await self.exchange.create_market_order(
                symbol, 
                side.lower(), 
                float(quantity)
            )
            
            logger.info(
                f"Orden de mercado ejecutada: {symbol} {side} {quantity} - "
                f"Order ID: {order['id']}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error colocando orden de mercado: {str(e)}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal
    ) -> Dict[str, Any]:
        """Coloca una orden límite."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            order = await self.exchange.create_limit_order(
                symbol,
                side.lower(),
                float(quantity),
                float(price)
            )
            
            logger.info(
                f"Orden límite colocada: {symbol} {side} {quantity} @ {price} - "
                f"Order ID: {order['id']}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error colocando orden límite: {str(e)}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancela una orden."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Orden cancelada: {symbol} - Order ID: {order_id}")
            return True
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(f"Orden no encontrada: {order_id}")
                return False
            logger.error(f"Error cancelando orden: {str(e)}")
            raise
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una orden."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            
            logger.debug(
                f"Estado de orden {order_id}: {order['status']} - "
                f"Filled: {order['filled']}/{order['amount']}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de orden: {str(e)}")
            raise
    
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtiene datos históricos de velas."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            # Convertir interval de Binance a CCXT
            ccxt_timeframe = self._convert_timeframe(interval)
            
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol, 
                ccxt_timeframe, 
                limit=limit
            )
            
            # Formatear datos
            formatted_klines = []
            for candle in ohlcv:
                formatted_klines.append({
                    'timestamp': candle[0],
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': Decimal(str(candle[5])),
                    'close_time': candle[0] + self._timeframe_to_ms(ccxt_timeframe),
                    'quote_volume': Decimal('0'),  # CCXT no proporciona esto
                    'trades': 0  # CCXT no proporciona esto
                })
            
            logger.debug(f"Obtenidas {len(formatted_klines)} velas para {symbol}")
            return formatted_klines
            
        except Exception as e:
            logger.error(f"Error obteniendo klines: {str(e)}")
            raise
    
    async def get_trading_fee(self, symbol: str) -> float:
        """Obtiene la comisión de trading para un símbolo."""
        await self._ensure_initialized()
        
        if not self.exchange:
            raise RuntimeError("Exchange no inicializado")
        
        try:
            # Obtener información de comisiones del mercado
            markets = self.exchange.markets
            if symbol in markets:
                market = markets[symbol]
                maker_fee = market.get('maker', 0.001)  # Default 0.1%
                logger.debug(f"Comisión para {symbol}: {maker_fee}")
                return maker_fee
            
            # Comisión por defecto
            default_fee = 0.001  # 0.1%
            logger.warning(
                f"No se encontró comisión para {symbol}, usando default: {default_fee}"
            )
            return default_fee
            
        except Exception as e:
            logger.error(f"Error obteniendo comisión: {str(e)}")
            return 0.001
    
    def _convert_timeframe(self, binance_interval: str) -> str:
        """Convierte intervalos de Binance a CCXT."""
        timeframe_map = {
            '1m': '1m',
            '3m': '3m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d',
            '3d': '3d',
            '1w': '1w',
            '1M': '1M'
        }
        return timeframe_map.get(binance_interval, '1h')
    
    def _timeframe_to_ms(self, timeframe: str) -> int:
        """Convierte timeframe a milisegundos."""
        timeframe_ms = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
            '1M': 30 * 24 * 60 * 60 * 1000
        }
        return timeframe_ms.get(timeframe, 60 * 60 * 1000) 