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
        grid_calculator: GridCalculator
    ):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        self.grid_calculator = grid_calculator
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
            
            # Procesar cada bot activo
            for config in active_configs:
                try:
                    bot_stats = self._get_bot_stats(config)
                    bots_details.append(bot_stats)
                    
                    total_trades += bot_stats.get('trades_count', 0)
                    total_profit += Decimal(str(bot_stats.get('pnl', 0)))
                    
                except Exception as e:
                    logger.error(f"❌ Error obteniendo stats para {config.pair}: {e}")
                    continue
            
            # Eventos de riesgo (por ahora vacío, se puede expandir)
            risk_events = {
                'stop_loss': 0,
                'trailing_up': 0
            }
            
            summary = {
                'active_bots': len(active_configs),
                'total_trades': total_trades,
                'total_profit': float(total_profit),
                'total_account_balance': float(total_account_balance),
                'bots_details': bots_details,
                'risk_events': risk_events,
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
        
        Args:
            config: Configuración del bot
            
        Returns:
            Dict con estadísticas del bot
        """
        try:
            pair = config.pair
            
            # Obtener órdenes activas
            active_orders = self.grid_repository.get_active_orders(pair)
            
            # Contar órdenes por tipo (solo órdenes abiertas)
            open_orders = [o for o in active_orders if o.status == 'open']
            buy_orders = len([o for o in open_orders if o.side == 'buy'])
            sell_orders = len([o for o in open_orders if o.side == 'sell'])
            
            # Obtener precio actual
            current_price = self.exchange_service.get_current_price(pair)
            
            # Obtener balance asignado con detalles
            bot_balance = self.exchange_service.get_bot_allocated_balance(config)
            allocated_capital = bot_balance.get('allocated_capital', Decimal('0'))
            base_balance = bot_balance.get('base_balance', Decimal('0'))
            quote_balance = bot_balance.get('quote_balance', Decimal('0'))
            base_value_usdt = bot_balance.get('base_value_usdt', Decimal('0'))
            quote_value_usdt = bot_balance.get('quote_value_usdt', Decimal('0'))
            
            # Calcular P&L (simplificado - en producción se calcularía con trades reales)
            pnl = self._calculate_bot_pnl(config, active_orders, current_price)
            pnl_percent = (pnl / allocated_capital * 100) if allocated_capital > 0 else 0
            
            # Contar trades completados (simulado)
            trades_count = len([o for o in active_orders if o.status == 'filled'])
            
            stats = {
                'pair': pair,
                'current_price': float(current_price),
                'allocated_capital': float(allocated_capital),
                'capital_in_assets': float(base_value_usdt),  # Capital en cryptos
                'capital_in_usdt': float(quote_value_usdt),   # Capital en USDT
                'buy_orders': buy_orders,
                'sell_orders': sell_orders,
                'total_orders': buy_orders + sell_orders,
                'has_orders': (buy_orders + sell_orders) > 0,  # Para claridad
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

    def _calculate_bot_pnl(self, config: GridConfig, active_orders: List[GridOrder], current_price: Decimal) -> Decimal:
        """
        Calcula el P&L de un bot (simplificado).
        En producción, esto se calcularía con trades reales y posiciones.
        
        Args:
            config: Configuración del bot
            active_orders: Órdenes activas
            current_price: Precio actual
            
        Returns:
            P&L calculado
        """
        try:
            # Por ahora, calculamos un P&L simulado basado en órdenes de compra ejecutadas
            filled_buy_orders = [o for o in active_orders if o.side == 'buy' and o.status == 'filled']
            
            if not filled_buy_orders:
                return Decimal('0')
            
            # Calcular valor promedio de compra
            total_buy_value = sum(order.price * order.amount for order in filled_buy_orders)
            total_buy_amount = sum(order.amount for order in filled_buy_orders)
            
            if total_buy_amount == 0:
                return Decimal('0')
            
            avg_buy_price = total_buy_value / total_buy_amount
            
            # Calcular P&L basado en precio actual
            current_value = total_buy_amount * current_price
            pnl = current_value - total_buy_value
            
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