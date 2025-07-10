"""Manager para manejar múltiples pares de trend bot simultáneamente."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..domain.entities import TrendBotConfig as DomainTrendBotConfig
from ..domain.interfaces import (
    ITrendBotRepository, IBrainDirectiveRepository, IExchangeService,
    INotificationService, ITrendBotStateManager
)
from .trend_bot_cycle_use_case import TrendBotCycleUseCase

logger = logging.getLogger(__name__)


@dataclass
class PairBotInstance:
    """Instancia de bot para un par específico."""
    pair: str
    config: DomainTrendBotConfig
    cycle_use_case: TrendBotCycleUseCase
    is_active: bool = True
    last_cycle_time: Optional[datetime] = None
    last_trailing_check: Optional[datetime] = None


class MultiPairManager:
    """Manager para manejar múltiples pares de trend bot."""
    
    def __init__(
        self,
        repository: ITrendBotRepository,
        brain_repository: IBrainDirectiveRepository,
        exchange_service: IExchangeService,
        notification_service: INotificationService,
        state_manager: ITrendBotStateManager,
        telegram_chat_id: str
    ):
        self.repository = repository
        self.brain_repository = brain_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.state_manager = state_manager
        self.telegram_chat_id = telegram_chat_id
        
        # Diccionario de bots por par
        self.bot_instances: Dict[str, PairBotInstance] = {}
        self.is_running = False
        
    async def load_active_configs(self) -> List[DomainTrendBotConfig]:
        """Carga todas las configuraciones activas desde la base de datos."""
        try:
            from shared.database.session import get_db_session
            from shared.database.models import TrendBotConfig
            
            with get_db_session() as session:
                if session is None:
                    return []
                
                active_configs = session.query(TrendBotConfig).filter(
                    TrendBotConfig.telegram_chat_id == self.telegram_chat_id,
                    TrendBotConfig.is_active == True
                ).all()
                
                configs = []
                for db_config in active_configs:
                    from decimal import Decimal
                    config = DomainTrendBotConfig(
                        symbol=str(db_config.pair),
                        capital_allocation=Decimal(str(db_config.capital_allocation)),
                        trailing_stop_percent=float(str(db_config.trailing_stop_percent)),
                        sandbox_mode=True  # Por ahora siempre sandbox
                    )
                    configs.append(config)
                
                logger.info(f"📊 Cargadas {len(configs)} configuraciones activas")
                return configs
                
        except Exception as e:
            logger.error(f"Error cargando configuraciones activas: {str(e)}")
            return []
    
    async def initialize_bots(self) -> None:
        """Inicializa todos los bots para los pares activos."""
        try:
            logger.info("🚀 Inicializando bots multi-pair...")
            
            # Cargar configuraciones activas
            active_configs = await self.load_active_configs()
            
            if not active_configs:
                logger.warning("⚠️ No hay configuraciones activas encontradas")
                return
            
            # Crear instancias de bot para cada par
            for config in active_configs:
                await self._create_bot_instance(config)
            
            logger.info(f"✅ Inicializados {len(self.bot_instances)} bots")
            
        except Exception as e:
            logger.error(f"Error inicializando bots: {str(e)}", exc_info=True)
            raise
    
    async def _create_bot_instance(self, config: DomainTrendBotConfig) -> None:
        """Crea una instancia de bot para un par específico."""
        try:
            # Crear caso de uso del ciclo para este par
            cycle_use_case = TrendBotCycleUseCase(
                repository=self.repository,
                brain_repository=self.brain_repository,
                exchange_service=self.exchange_service,
                notification_service=self.notification_service,
                state_manager=self.state_manager,
                config=config
            )
            
            # Crear instancia del bot
            bot_instance = PairBotInstance(
                pair=config.symbol,
                config=config,
                cycle_use_case=cycle_use_case
            )
            
            # Agregar al diccionario
            self.bot_instances[config.symbol] = bot_instance
            
            logger.info(f"✅ Bot creado para {config.symbol}")
            
        except Exception as e:
            logger.error(f"Error creando bot para {config.symbol}: {str(e)}")
    
    async def execute_cycle_for_all_pairs(self) -> Dict[str, bool]:
        """Ejecuta un ciclo para todos los pares activos."""
        results = {}
        
        for pair, bot_instance in self.bot_instances.items():
            if not bot_instance.is_active:
                continue
                
            try:
                logger.debug(f"🔄 Ejecutando ciclo para {pair}")
                success = await bot_instance.cycle_use_case.execute_cycle()
                results[pair] = success
                bot_instance.last_cycle_time = datetime.utcnow()
                
                if success:
                    logger.debug(f"✅ Ciclo exitoso para {pair}")
                else:
                    logger.warning(f"⚠️ Ciclo con advertencias para {pair}")
                    
            except Exception as e:
                logger.error(f"❌ Error en ciclo para {pair}: {str(e)}")
                results[pair] = False
        
        return results
    
    async def check_trailing_stop_for_all_pairs(self) -> Dict[str, bool]:
        """Verifica trailing stop para todos los pares activos."""
        results = {}
        
        for pair, bot_instance in self.bot_instances.items():
            if not bot_instance.is_active:
                continue
                
            try:
                logger.debug(f"🔄 Verificando trailing stop para {pair}")
                await bot_instance.cycle_use_case.check_trailing_stop()
                results[pair] = True
                bot_instance.last_trailing_check = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"❌ Error verificando trailing stop para {pair}: {str(e)}")
                results[pair] = False
        
        return results
    
    async def reload_configs(self) -> None:
        """Recarga las configuraciones desde la base de datos."""
        try:
            logger.info("🔄 Recargando configuraciones...")
            
            # Cargar configuraciones actuales
            active_configs = await self.load_active_configs()
            active_pairs = {config.symbol for config in active_configs}
            
            # Desactivar bots que ya no están activos
            for pair in list(self.bot_instances.keys()):
                if pair not in active_pairs:
                    logger.info(f"🛑 Desactivando bot para {pair}")
                    self.bot_instances[pair].is_active = False
            
            # Crear bots para nuevos pares activos
            for config in active_configs:
                if config.symbol not in self.bot_instances:
                    await self._create_bot_instance(config)
                else:
                    # Actualizar configuración existente
                    self.bot_instances[config.symbol].config = config
                    logger.info(f"✅ Configuración actualizada para {config.symbol}")
            
            logger.info(f"🔄 Recarga completada: {len(active_configs)} pares activos")
            
        except Exception as e:
            logger.error(f"Error recargando configuraciones: {str(e)}")
    
    def get_status(self) -> Dict:
        """Obtiene el estado de todos los bots."""
        status = {
            "is_running": self.is_running,
            "total_bots": len(self.bot_instances),
            "active_bots": sum(1 for bot in self.bot_instances.values() if bot.is_active),
            "bots": {}
        }
        
        for pair, bot_instance in self.bot_instances.items():
            status["bots"][pair] = {
                "is_active": bot_instance.is_active,
                "capital_allocation": str(bot_instance.config.capital_allocation),
                "trailing_stop_percent": bot_instance.config.trailing_stop_percent,
                "last_cycle_time": bot_instance.last_cycle_time.isoformat() if bot_instance.last_cycle_time else None,
                "last_trailing_check": bot_instance.last_trailing_check.isoformat() if bot_instance.last_trailing_check else None
            }
        
        return status
    
    def get_active_pairs(self) -> List[str]:
        """Obtiene la lista de pares activos."""
        return [pair for pair, bot in self.bot_instances.items() if bot.is_active] 