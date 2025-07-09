"""
Caso de uso para generar estadísticas de trading para notificaciones.
"""
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from app.domain.interfaces import GridRepository, ExchangeService, GridCalculator
from app.domain.entities import GridConfig, GridOrder
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class TradingStatsUseCase:
    """
    Caso de uso para generar estadísticas de trading para notificaciones.
    
    Responsabilidades:
    - Generar estadísticas generales de todos los bots
    - Calcular P&L por par
    - Contar órdenes activas
    - Obtener precios actuales
    - Preparar datos para resúmenes periódicos
    """
    
    def __init__(
        self,
        grid_repository: GridRepository,
        exchange_service: ExchangeService,
        grid_calculator: GridCalculator,
        realtime_monitor_use_case=None  # Opcional para obtener notificaciones acumuladas
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.grid_calculator = grid_calculator
        self.realtime_monitor_use_case = realtime_monitor_use_case
        logger.info("✅ TradingStatsUseCase inicializado.")

    def generate_trading_summary(self) -> Dict[str, Any]:
        """
        Genera un resumen completo de trading para notificaciones.
        
        Returns:
            Dict con estadísticas de trading
        """
        try:
            # Obtener configuraciones activas
            active_configs = self.grid_repository.get_active_configs()
            
            if not active_configs:
                return {
                    'active_bots': 0,
                    'total_trades': 0,
                    'total_profit': 0.0,
                    'total_account_balance': 0.0,
                    'bots_details': [],
                    'risk_events': {}
                }
            
            # Obtener balance total de la cuenta
            total_account_balance = self._get_total_account_balance()
            
            # Estadísticas generales
            total_trades = 0
            total_profit = Decimal('0')
            bots_details = []
            
            # 📊 Obtener trades acumulados del monitor tiempo real
            if self.realtime_monitor_use_case:
                total_trades = self.realtime_monitor_use_case.get_total_trades_count()
                logger.info(f"📊 Total trades acumulados: {total_trades}")
            
            # Procesar cada bot activo
            for config in active_configs:
                try:
                    bot_stats = self._get_bot_stats(config)
                    bots_details.append(bot_stats)
                    
                    # No sumar trades_count aquí, ya se obtiene del monitor tiempo real
                    total_profit += Decimal(str(bot_stats.get('pnl', 0)))
                    
                except Exception as e:
                    logger.error(f"❌ Error obteniendo stats para {config.pair}: {e}")
                    continue
            
            # Eventos de riesgo (por ahora vacío, se puede expandir)
            risk_events = {
                'stop_loss': 0,
                'trailing_up': 0
            }
            
            # 📱 Obtener resumen de órdenes complementarias acumuladas
            complementary_orders_summary = ""
            if self.realtime_monitor_use_case:
                complementary_orders_summary = self.realtime_monitor_use_case.format_complementary_orders_summary()
            
            summary = {
                'active_bots': len(active_configs),
                'total_trades': total_trades,
                'total_profit': float(total_profit),
                'total_account_balance': float(total_account_balance),
                'bots_details': bots_details,
                'risk_events': risk_events,
                'complementary_orders_summary': complementary_orders_summary,
                'timestamp': datetime.now()
            }
            
            logger.debug(f"📊 Resumen generado: {len(active_configs)} bots, {total_trades} trades, ${total_profit:.4f}, Balance total: ${total_account_balance:.2f}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen de trading: {e}")
            return {
                'active_bots': 0,
                'total_trades': 0,
                'total_profit': 0.0,
                'total_account_balance': 0.0,
                'bots_details': [],
                'risk_events': {},
                'error': str(e)
            }

    def _get_total_account_balance(self) -> Decimal:
        """
        Obtiene el balance total de la cuenta en USDT.
        
        Returns:
            Balance total en USDT
        """
        try:
            # Obtener balance de USDT
            usdt_balance = self.exchange_service.get_balance('USDT')
            
            # Obtener todos los pares activos para calcular valor de cryptos
            active_configs = self.grid_repository.get_active_configs()
            total_crypto_value = Decimal('0')
            
            for config in active_configs:
                try:
                    pair = config.pair
                    base_currency = pair.split('/')[0]
                    
                    # Obtener balance de la crypto
                    crypto_balance = self.exchange_service.get_balance(base_currency)
                    
                    if crypto_balance > 0:
                        # Obtener precio actual
                        current_price = self.exchange_service.get_current_price(pair)
                        crypto_value = crypto_balance * current_price
                        total_crypto_value += crypto_value
                        
                        logger.debug(f"💰 {base_currency}: {crypto_balance} (${crypto_value:.2f})")
                        
                except Exception as e:
                    logger.error(f"❌ Error calculando valor de {config.pair}: {e}")
                    continue
            
            total_balance = usdt_balance + total_crypto_value
            logger.debug(f"💰 Balance total cuenta: ${usdt_balance:.2f} USDT + ${total_crypto_value:.2f} cryptos = ${total_balance:.2f}")
            
            return total_balance
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance total: {e}")
            return Decimal('0')

    def _get_bot_stats(self, config: GridConfig) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas para un bot específico.
        MEJORADO: Usa datos reales del exchange en lugar de la base de datos local.
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con estadísticas del bot
        """
        try:
            pair = config.pair
            
            # Obtener órdenes activas directamente del exchange
            exchange_orders = self.exchange_service.get_active_orders_from_exchange(pair)
            
            # Contar órdenes por tipo (solo órdenes abiertas del exchange)
            buy_orders = len([o for o in exchange_orders if o['side'] == 'buy'])
            sell_orders = len([o for o in exchange_orders if o['side'] == 'sell'])
            
            # Obtener precio actual
            current_price = self.exchange_service.get_current_price(pair)
            
            # Obtener balances reales directamente del exchange
            real_balances = self.exchange_service.get_real_balances_from_exchange(pair)
            base_balance = real_balances.get('base_balance', Decimal('0'))
            quote_balance = real_balances.get('quote_balance', Decimal('0'))
            base_value_usdt = real_balances.get('base_value_usdt', Decimal('0'))
            quote_value_usdt = real_balances.get('quote_value_usdt', Decimal('0'))
            
            # Calcular capital bloqueado en órdenes de venta
            sell_orders_list = [o for o in exchange_orders if o['side'] == 'sell']
            locked_base_amount = sum(Decimal(str(order['amount'])) for order in sell_orders_list)
            locked_base_value_usdt = locked_base_amount * current_price
            
            # Capital total en activos = libre + bloqueado
            total_base_value_usdt = base_value_usdt + locked_base_value_usdt
            
            # Obtener balance asignado para comparación
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            allocated_capital = bot_balance.get('allocated_capital', Decimal('0'))
            
            # Calcular P&L (simplificado - en producción se calcularía con trades reales)
            # Usar órdenes de la base de datos para el cálculo de P&L
            # active_orders = self.grid_repository.get_active_orders(pair)
            active_orders = self.exchange_service.get_active_orders_from_exchange(pair)
            pnl = self._calculate_bot_pnl(config, active_orders, current_price)
            pnl_percent = (pnl / allocated_capital * 100) if allocated_capital > 0 else 0
            
            # 📊 Contar trades reales acumulados del monitor tiempo real
            trades_count = 0
            if self.realtime_monitor_use_case:
                # Obtener trades acumulados para este par específico
                trades_count = self.realtime_monitor_use_case.get_trades_count_by_pair(pair)
                logger.debug(f"📊 {pair}: {trades_count} trades acumulados del monitor tiempo real")
            else:
                # Fallback: contar trades desde la base de datos (si existe)
                try:
                    # Aquí podrías implementar conteo desde la base de datos si tienes una tabla de trades
                    trades_count = 0
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo obtener trades desde BD para {pair}: {e}")
                    trades_count = 0
            
            stats = {
                'pair': pair,
                'current_price': float(current_price),
                'allocated_capital': float(allocated_capital),
                'capital_in_assets': float(total_base_value_usdt),  # Capital total en cryptos (libre + bloqueado)
                'capital_in_assets_free': float(base_value_usdt),   # Capital libre en cryptos
                'capital_in_assets_locked': float(locked_base_value_usdt),  # Capital bloqueado en órdenes de venta
                'capital_in_usdt': float(quote_value_usdt),   # Capital real en USDT
                'buy_orders': buy_orders,
                'sell_orders': sell_orders,
                'total_orders': buy_orders + sell_orders,
                'has_orders': (buy_orders + sell_orders) > 0,  # Para claridad
                'grid_levels': config.grid_levels,  # Límite de órdenes activas
                'pnl': float(pnl),
                'pnl_percent': float(pnl_percent),
                'trades_count': trades_count,
                'is_active': config.is_running,
                'last_decision': config.last_decision,
                'base_balance': float(base_balance),
                'quote_balance': float(quote_balance)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats para {config.pair}: {e}")
            return {
                'pair': config.pair,
                'current_price': 0.0,
                'allocated_capital': 0.0,
                'capital_in_assets': 0.0,
                'capital_in_usdt': 0.0,
                'buy_orders': 0,
                'sell_orders': 0,
                'total_orders': 0,
                'has_orders': False,
                'pnl': 0.0,
                'pnl_percent': 0.0,
                'trades_count': 0,
                'is_active': False,
                'base_balance': 0.0,
                'quote_balance': 0.0,
                'error': str(e)
            }

    def _calculate_bot_pnl(self, config: GridConfig, active_orders: List[Dict[str, Any]], current_price: Decimal) -> Decimal:
        """
        Calcula el P&L real de un bot basado en balances actuales y capital inicial.
        
        Args:
            config: Configuración del bot
            active_orders: Órdenes activas (dicts del exchange)
            current_price: Precio actual
            
        Returns:
            P&L calculado
        """
        try:
            # Obtener balance actual del bot
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            current_total_value = bot_balance.get('total_value_usdt', Decimal('0'))
            allocated_capital = bot_balance.get('allocated_capital', Decimal('0'))
            
            # Obtener balances reales del exchange
            real_balances = self.exchange_service.get_real_balances_from_exchange(config.pair)
            base_balance = real_balances.get('base_balance', Decimal('0'))
            quote_balance = real_balances.get('quote_balance', Decimal('0'))
            
            # Calcular valor actual de los activos
            base_value_usdt = base_balance * current_price
            total_current_value = base_value_usdt + quote_balance
            
            # Calcular P&L real: Valor actual - Capital inicial asignado
            pnl = total_current_value - allocated_capital
            
            logger.debug(f"📊 P&L cálculo para {config.pair}:")
            logger.debug(f"   Capital asignado: ${allocated_capital:.2f}")
            logger.debug(f"   Balance base: {base_balance} (${base_value_usdt:.2f})")
            logger.debug(f"   Balance quote: ${quote_balance:.2f}")
            logger.debug(f"   Valor total actual: ${total_current_value:.2f}")
            logger.debug(f"   P&L: ${pnl:.2f}")
            
            return pnl
            
        except Exception as e:
            logger.error(f"❌ Error calculando P&L para {config.pair}: {e}")
            return Decimal('0')

    def get_decision_changes(self) -> List[tuple]:
        """
        Obtiene cambios de decisión recientes.
        
        Returns:
            Lista de tuplas (GridConfig, current_decision, previous_state)
        """
        try:
            return self.grid_repository.get_configs_with_decisions()
        except Exception as e:
            logger.error(f"❌ Error obteniendo cambios de decisión: {e}")
            return []

    def get_risk_events_summary(self) -> Dict[str, int]:
        """
        Obtiene resumen de eventos de riesgo recientes.
        
        Returns:
            Dict con conteo de eventos de riesgo
        """
        try:
            # Por ahora retornamos valores simulados
            # En producción, esto se obtendría de logs o base de datos
            return {
                'stop_loss': 0,
                'trailing_up': 0
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de eventos de riesgo: {e}")
            return {
                'stop_loss': 0,
                'trailing_up': 0
            }

    def get_bot_performance_summary(self, pair: str) -> Dict[str, Any]:
        """
        Obtiene resumen de performance de un bot específico.
        
        Args:
            pair: Par de trading
            
        Returns:
            Dict con resumen de performance
        """
        try:
            config = self.grid_repository.get_config_by_pair(pair)
            if not config:
                return {}
            
            return self._get_bot_stats(config)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo performance para {pair}: {e}")
            return {}

    def get_all_bots_status(self) -> List[Dict[str, Any]]:
        """
        Obtiene estado de todos los bots.
        
        Returns:
            Lista con estado de cada bot
        """
        try:
            active_configs = self.grid_repository.get_active_configs()
            status_list = []
            
            for config in active_configs:
                status = {
                    'pair': config.pair,
                    'is_running': config.is_running,
                    'last_decision': config.last_decision,
                    'total_capital': config.total_capital,
                    'config_type': config.config_type
                }
                status_list.append(status)
            
            return status_list
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de bots: {e}")
            return [] 

# Ejemplo de uso del cálculo de P&L mejorado:
"""
# Ejemplo de uso del cálculo de P&L real:

# 1. El método _calculate_bot_pnl ahora calcula P&L real:
#    - Obtiene balance actual del bot (base + quote)
#    - Calcula valor total actual en USDT
#    - Resta el capital inicial asignado
#    - Resultado: P&L real basado en balances actuales

# 2. Ejemplo de cálculo:
#    - Capital asignado: $300.00 USDT
#    - Balance actual: 0.1 ETH ($275.00) + $25.00 USDT = $300.00
#    - P&L = $300.00 - $300.00 = $0.00 (break-even)
#    - Si ETH sube a $2800: P&L = $280.00 + $25.00 - $300.00 = $5.00 (ganancia)

# 3. Ventajas del nuevo cálculo:
#    - Basado en balances reales del exchange
#    - Considera comisiones y slippage
#    - Refleja ganancias/pérdidas reales
#    - No depende de órdenes activas
""" 