"""
Caso de uso para generar resumen detallado del estado de trading.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.domain.interfaces import GridRepository, ExchangeService, NotificationService
from app.domain.entities import GridConfig
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class BotStatus:
    """Estado detallado de un bot individual."""
    pair: str
    is_active: bool
    is_running: bool
    is_configured: bool
    total_capital: float
    allocated_capital: float
    available_capital: float
    current_price: float
    grid_levels: int
    price_range_percent: float
    last_decision: str
    active_orders_count: int
    total_orders_created: int
    status_summary: str

@dataclass
class TradingSummary:
    """Resumen completo del estado de trading."""
    total_bots: int
    active_bots: int
    paused_bots: int
    total_capital_allocated: float
    total_capital_available: float
    total_orders_active: int
    bots_status: List[BotStatus]
    exchange_balance: Dict[str, float]
    trading_mode: str
    last_update: datetime

class TradingStatusUseCase:
    """
    Genera resumen detallado del estado de todos los bots de trading.
    """
    
    def __init__(
        self, 
        repository: GridRepository, 
        exchange_service: ExchangeService,
        notification_service: NotificationService
    ):
        self.repository = repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        logger.info("✅ TradingStatusUseCase inicializado.")

    def generate_detailed_status(self) -> TradingSummary:
        """
        Genera un resumen detallado del estado de todos los bots.
        
        Returns:
            TradingSummary: Resumen completo del estado de trading
        """
        try:
            logger.info("📊 Generando resumen detallado del estado de trading...")
            
            # Obtener todas las configuraciones
            configs_with_decisions = self.repository.get_configs_with_decisions()
            
            # Obtener balance del exchange
            exchange_balance = self._get_exchange_balance()
            
            # Obtener modo de trading
            trading_mode = self.exchange_service.get_trading_mode()
            
            # Procesar cada configuración
            bots_status = []
            total_capital_allocated = 0.0
            total_capital_available = 0.0
            total_orders_active = 0
            
            for config, current_decision, previous_state in configs_with_decisions:
                bot_status = self._analyze_bot_status(config, current_decision, exchange_balance)
                bots_status.append(bot_status)
                
                if bot_status.is_active:
                    total_capital_allocated += bot_status.allocated_capital
                    total_orders_active += bot_status.active_orders_count
            
            # Calcular capital disponible total
            total_capital_available = exchange_balance.get('USDT', 0.0)
            
            # Contar bots por estado
            active_bots = sum(1 for bot in bots_status if bot.is_active and bot.is_running)
            paused_bots = sum(1 for bot in bots_status if bot.is_active and not bot.is_running)
            
            summary = TradingSummary(
                total_bots=len(bots_status),
                active_bots=active_bots,
                paused_bots=paused_bots,
                total_capital_allocated=total_capital_allocated,
                total_capital_available=total_capital_available,
                total_orders_active=total_orders_active,
                bots_status=bots_status,
                exchange_balance=exchange_balance,
                trading_mode=trading_mode,
                last_update=datetime.utcnow()
            )
            
            logger.info(f"✅ Resumen generado: {active_bots} bots activos, {paused_bots} pausados")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen detallado: {e}")
            raise

    def _analyze_bot_status(
        self, 
        config: GridConfig, 
        current_decision: str, 
        exchange_balance: Dict[str, float]
    ) -> BotStatus:
        """
        Analiza el estado detallado de un bot individual.
        
        Args:
            config: Configuración del bot
            current_decision: Decisión actual del cerebro
            exchange_balance: Balance del exchange
            
        Returns:
            BotStatus: Estado detallado del bot
        """
        try:
            # Obtener precio actual
            current_price = self._get_current_price(config.pair)
            
            # Calcular capital asignado y disponible
            allocated_capital = config.total_capital
            available_capital = exchange_balance.get('USDT', 0.0)
            
            # Obtener órdenes activas
            active_orders = self.repository.get_active_orders(config.pair)
            active_orders_count = len(active_orders)
            
            # Calcular órdenes totales creadas (simulado por ahora)
            total_orders_created = config.grid_levels * 2  # Compra + Venta por nivel
            
            # Determinar estado del bot
            if config.is_active and config.is_running:
                if current_decision == "BUY":
                    status_summary = "🟢 ACTIVO - Comprando"
                elif current_decision == "SELL":
                    status_summary = "🟢 ACTIVO - Vendiendo"
                elif current_decision == "HOLD":
                    status_summary = "🟡 ACTIVO - En espera"
                else:
                    status_summary = "🟢 ACTIVO - Monitoreando"
            elif config.is_active and not config.is_running:
                status_summary = "⏸️ PAUSADO"
            else:
                status_summary = "🔴 INACTIVO"
            
            return BotStatus(
                pair=config.pair,
                is_active=config.is_active,
                is_running=config.is_running,
                is_configured=config.is_configured,
                total_capital=config.total_capital,
                allocated_capital=allocated_capital,
                available_capital=available_capital,
                current_price=current_price,
                grid_levels=config.grid_levels,
                price_range_percent=config.price_range_percent,
                last_decision=current_decision,
                active_orders_count=active_orders_count,
                total_orders_created=total_orders_created,
                status_summary=status_summary
            )
            
        except Exception as e:
            logger.error(f"❌ Error analizando estado del bot {config.pair}: {e}")
            # Retornar estado básico en caso de error
            return BotStatus(
                pair=config.pair,
                is_active=config.is_active,
                is_running=config.is_running,
                is_configured=config.is_configured,
                total_capital=config.total_capital,
                allocated_capital=0.0,
                available_capital=0.0,
                current_price=0.0,
                grid_levels=config.grid_levels,
                price_range_percent=config.price_range_percent,
                last_decision=current_decision,
                active_orders_count=0,
                total_orders_created=0,
                status_summary="❌ ERROR"
            )

    def _get_exchange_balance(self) -> Dict[str, float]:
        """
        Obtiene el balance actual del exchange.
        
        Returns:
            Dict[str, float]: Balance por moneda
        """
        try:
            # Obtener solo USDT por ahora (implementación simplificada)
            usdt_balance = self.exchange_service.get_balance('USDT')
            result = {'USDT': float(usdt_balance)}
            logger.info(f"💰 Balance obtenido: {len(result)} monedas")
            return result
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance: {e}")
            return {'USDT': 0.0}

    def _get_current_price(self, pair: str) -> float:
        """
        Obtiene el precio actual de un par.
        
        Args:
            pair: Par de trading
            
        Returns:
            float: Precio actual
        """
        try:
            # Usar el método get_current_price que ya existe
            price = self.exchange_service.get_current_price(pair)
            return float(price)
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de {pair}: {e}")
            return 0.0

    def send_detailed_status_notification(self) -> None:
        """(OBSOLETO) Enviar notificación de estado detallado (ya no se usa)."""
        pass

    def format_status_message(self, summary: TradingSummary) -> str:
        """
        Formatea el resumen como mensaje legible.
        
        Args:
            summary: Resumen del estado de trading
            
        Returns:
            str: Mensaje formateado
        """
        try:
            message = f"📊 **ESTADO DETALLADO DE TRADING**\n\n"
            message += f"🕐 Actualizado: {summary.last_update.strftime('%H:%M:%S %d/%m/%Y')}\n"
            message += f"💱 Modo: {summary.trading_mode.upper()}\n\n"
            
            # Resumen general
            message += f"**📈 RESUMEN GENERAL**\n"
            message += f"• Total de bots: {summary.total_bots}\n"
            message += f"• Bots activos: {summary.active_bots} 🟢\n"
            message += f"• Bots pausados: {summary.paused_bots} ⏸️\n"
            message += f"• Capital asignado: ${summary.total_capital_allocated:,.2f} USDT\n"
            message += f"• Capital disponible: ${summary.total_capital_available:,.2f} USDT\n"
            message += f"• Órdenes activas: {summary.total_orders_active}\n\n"
            
            # Balance del exchange
            message += f"**💰 BALANCE DEL EXCHANGE**\n"
            for currency, amount in summary.exchange_balance.items():
                if amount > 0:
                    message += f"• {currency}: {amount:,.8f}\n"
            message += "\n"
            
            # Estado de cada bot
            message += f"**🤖 ESTADO DE BOTS**\n"
            for bot in summary.bots_status:
                if bot.is_active:  # Solo mostrar bots activos
                    message += f"\n**{bot.pair}** {bot.status_summary}\n"
                    message += f"• Capital: ${bot.allocated_capital:,.2f} USDT\n"
                    message += f"• Precio actual: ${bot.current_price:,.8f}\n"
                    message += f"• Niveles: {bot.grid_levels} | Rango: {bot.price_range_percent}%\n"
                    message += f"• Órdenes activas: {bot.active_orders_count}\n"
                    message += f"• Última decisión: {bot.last_decision}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando mensaje de estado: {e}")
            return f"❌ Error generando estado detallado: {e}" 