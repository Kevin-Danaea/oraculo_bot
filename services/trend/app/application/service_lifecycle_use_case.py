"""Use case for managing the trend bot service lifecycle."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..domain.entities import TrendBotConfig
from ..domain.interfaces import (
    ITrendBotRepository, IBrainDirectiveRepository, IExchangeService,
    INotificationService, ITrendBotStateManager
)
from .trend_bot_cycle_use_case import TrendBotCycleUseCase

logger = logging.getLogger(__name__)


class ServiceLifecycleUseCase:
    """Caso de uso para gestionar el ciclo de vida del servicio trend bot."""
    
    def __init__(
        self,
        repository: ITrendBotRepository,
        brain_repository: IBrainDirectiveRepository,
        exchange_service: IExchangeService,
        notification_service: INotificationService,
        state_manager: ITrendBotStateManager,
        config: TrendBotConfig
    ):
        self.repository = repository
        self.brain_repository = brain_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.state_manager = state_manager
        self.config = config
        
        # Crear caso de uso del ciclo
        self.cycle_use_case = TrendBotCycleUseCase(
            repository=repository,
            brain_repository=brain_repository,
            exchange_service=exchange_service,
            notification_service=notification_service,
            state_manager=state_manager,
            config=config
        )
        
        self.is_running = False
        self.cycle_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Inicia el servicio y sus tareas programadas."""
        if self.is_running:
            logger.warning("El servicio ya está en ejecución")
            return
            
        logger.info("🚀 Iniciando servicio Trend Following Bot...")
        self.is_running = True
        
        try:
            # Notificar inicio
            await self.notification_service.send_startup_notification(self.config)
            
            # Iniciar tarea principal
            self.cycle_task = asyncio.create_task(self._main_cycle_loop())
            
            logger.info("✅ Servicio Trend Following Bot iniciado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando servicio: {str(e)}", exc_info=True)
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """Detiene el servicio y cancela todas las tareas."""
        if not self.is_running:
            logger.warning("El servicio no está en ejecución")
            return
            
        logger.info("🛑 Deteniendo servicio Trend Following Bot...")
        self.is_running = False
        
        # Cancelar tarea principal
        if self.cycle_task:
            self.cycle_task.cancel()
            try:
                await self.cycle_task
            except asyncio.CancelledError:
                pass
        
        # Notificar detención
        await self.notification_service.send_error_notification(
            "🛑 Trend Following Bot detenido",
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        logger.info("✅ Servicio detenido exitosamente")
    
    async def _main_cycle_loop(self) -> None:
        """Loop principal del servicio."""
        cycle_interval_hours = 1  # Ciclo cada 1 hora
        
        logger.info(f"🔄 Iniciando loop principal con intervalo de {cycle_interval_hours} hora(s)")
        
        while self.is_running:
            try:
                # Ejecutar ciclo de operación
                success = await self.cycle_use_case.execute_cycle()
                
                if success:
                    logger.debug("✅ Ciclo ejecutado exitosamente")
                else:
                    logger.warning("⚠️ Ciclo ejecutado con advertencias")
                
            except asyncio.CancelledError:
                logger.info("🛑 Loop principal cancelado")
                break
            except Exception as e:
                logger.error(f"❌ Error en loop principal: {str(e)}", exc_info=True)
                await self.notification_service.send_error_notification(
                    f"Error crítico en loop principal: {str(e)}",
                    {"timestamp": datetime.utcnow().isoformat()}
                )
            
            # Esperar hasta el próximo ciclo
            if self.is_running:
                logger.debug(f"⏰ Esperando {cycle_interval_hours} hora(s) hasta el próximo ciclo")
                await asyncio.sleep(cycle_interval_hours * 3600)
    
    def get_status(self) -> dict:
        """Obtiene el estado actual del servicio."""
        return {
            "is_running": self.is_running,
            "symbol": self.config.symbol,
            "capital_allocation": str(self.config.capital_allocation),
            "trailing_stop_percent": self.config.trailing_stop_percent,
            "sandbox_mode": self.config.sandbox_mode,
            "cycle_task_running": self.cycle_task is not None and not self.cycle_task.done(),
            "timestamp": datetime.utcnow().isoformat()
        } 