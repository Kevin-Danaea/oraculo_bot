"""
Caso de uso para obtener el estado general del sistema Grid Trading.
"""
from typing import Dict, Any, List
from datetime import datetime

from app.domain.interfaces import GridRepository, ExchangeService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GetSystemStatusUseCase:
    """Caso de uso para obtener información de estado del sistema."""
    
    def __init__(self, grid_repository: GridRepository, exchange_service: ExchangeService):
        self.grid_repository = grid_repository
        self.exchange_service = exchange_service
        
    def execute(self) -> Dict[str, Any]:
        """Ejecuta la obtención del estado del sistema."""
        try:
            logger.info("📊 Obteniendo estado del sistema Grid Trading...")
            
            # Obtener configuraciones activas
            active_configs = self.grid_repository.get_active_configs()
            
            # Información de configuraciones por par
            config_info = {}
            total_capital = 0.0
            
            for config in active_configs:
                try:
                    # Obtener precio actual del par
                    current_price = self.exchange_service.get_current_price(config.pair)
                    
                    config_info[config.pair] = {
                        "id": config.id,
                        "total_capital": config.total_capital,
                        "grid_levels": config.grid_levels,
                        "price_range_percent": config.price_range_percent,
                        "current_price": float(current_price),
                        "is_running": config.is_running,
                        "last_decision": config.last_decision,
                        "last_decision_timestamp": config.last_decision_timestamp.isoformat() if config.last_decision_timestamp else None,
                        "created_at": config.created_at.isoformat() if config.created_at else None,
                        "updated_at": config.updated_at.isoformat() if config.updated_at else None
                    }
                    
                    total_capital += config.total_capital
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error obteniendo info de {config.pair}: {e}")
                    config_info[config.pair] = {
                        "id": config.id,
                        "error": str(e),
                        "total_capital": config.total_capital
                    }
            
            # Información del exchange
            trading_mode = self.exchange_service.get_trading_mode()
            
            # Balances (solo para pares configurados)
            balances = {}
            base_currencies = set()
            quote_currencies = set()
            
            for config in active_configs:
                pair_parts = config.pair.split('/')
                if len(pair_parts) == 2:
                    base_currencies.add(pair_parts[0])
                    quote_currencies.add(pair_parts[1])
            
            all_currencies = base_currencies.union(quote_currencies)
            
            for currency in all_currencies:
                try:
                    balance = self.exchange_service.get_balance(currency)
                    balances[currency] = float(balance)
                except Exception as e:
                    logger.warning(f"⚠️ Error obteniendo balance de {currency}: {e}")
                    balances[currency] = {"error": str(e)}
            
            # Crear resumen del estado
            status_summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_active_bots": len(active_configs),
                "total_capital_allocated": total_capital,
                "trading_mode": trading_mode,
                "supported_pairs": list(config_info.keys()),
                "configurations": config_info,
                "balances": balances,
                "system_health": {
                    "database": "connected",
                    "exchange": "connected" if self.exchange_service else "disconnected",
                    "trading_mode": trading_mode
                }
            }
            
            logger.info(f"✅ Estado obtenido: {len(active_configs)} bots, capital total: ${total_capital:.2f}")
            
            return {
                "success": True,
                "data": status_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del sistema: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_active_bots": 0,
                    "error": str(e)
                }
            } 