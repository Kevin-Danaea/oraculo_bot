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
from .multi_pair_manager import MultiPairManager

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
        telegram_chat_id: str
    ):
        self.repository = repository
        self.brain_repository = brain_repository
        self.exchange_service = exchange_service
        self.notification_service = notification_service
        self.state_manager = state_manager
        self.telegram_chat_id = telegram_chat_id
        
        # Crear manager multi-par
        self.multi_pair_manager = MultiPairManager(
            repository=repository,
            brain_repository=brain_repository,
            exchange_service=exchange_service,
            notification_service=notification_service,
            state_manager=state_manager,
            telegram_chat_id=telegram_chat_id
        )
        
        self.is_running = False
        self.cycle_task: Optional[asyncio.Task] = None
        self.trailing_stop_task: Optional[asyncio.Task] = None
        self.config_reload_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Inicia el servicio y sus tareas programadas."""
        if self.is_running:
            logger.warning("El servicio ya está en ejecución")
            return
            
        logger.info("🚀 Iniciando servicio Trend Following Bot Multi-Par...")
        self.is_running = True
        
        try:
            # Inicializar bots multi-par
            await self.multi_pair_manager.initialize_bots()
            
            # Notificar inicio
            active_pairs = self.multi_pair_manager.get_active_pairs()
            await self.notification_service.send_error_notification(
                f"🚀 Trend Following Bot Multi-Par iniciado con {len(active_pairs)} pares activos",
                {
                    "telegram_chat_id": self.telegram_chat_id,
                    "active_pairs": active_pairs,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Iniciar tarea principal
            self.cycle_task = asyncio.create_task(self._main_cycle_loop())
            
            # Iniciar tarea de monitoreo de trailing stop
            self.trailing_stop_task = asyncio.create_task(self._trailing_stop_monitor_loop())
            
            # Iniciar tarea de recarga de configuraciones
            self.config_reload_task = asyncio.create_task(self._config_reload_loop())
            
            logger.info("✅ Servicio Trend Following Bot Multi-Par iniciado correctamente")
            
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
        
        # Cancelar tarea de trailing stop
        if self.trailing_stop_task:
            self.trailing_stop_task.cancel()
            try:
                await self.trailing_stop_task
            except asyncio.CancelledError:
                pass
        
        # Cancelar tarea de recarga de configuraciones
        if self.config_reload_task:
            self.config_reload_task.cancel()
            try:
                await self.config_reload_task
            except asyncio.CancelledError:
                pass
        
        # Notificar detención
        await self.notification_service.send_error_notification(
            "🛑 Trend Following Bot Multi-Par detenido",
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        logger.info("✅ Servicio detenido exitosamente")
    
    async def _main_cycle_loop(self) -> None:
        """Loop principal del servicio para todos los pares."""
        cycle_interval_hours = 1  # Ciclo cada 1 hora
        
        logger.info(f"🔄 Iniciando loop principal multi-par con intervalo de {cycle_interval_hours} hora(s)")
        
        while self.is_running:
            try:
                # Ejecutar ciclo para todos los pares activos
                results = await self.multi_pair_manager.execute_cycle_for_all_pairs()
                
                successful_pairs = [pair for pair, success in results.items() if success]
                failed_pairs = [pair for pair, success in results.items() if not success]
                
                if successful_pairs:
                    logger.debug(f"✅ Ciclos exitosos para: {', '.join(successful_pairs)}")
                if failed_pairs:
                    logger.warning(f"⚠️ Ciclos con advertencias para: {', '.join(failed_pairs)}")
                
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
    
    async def _trailing_stop_monitor_loop(self) -> None:
        """Loop de monitoreo de trailing stop cada 5-10 minutos para todos los pares."""
        monitor_interval_minutes = 5  # Monitoreo cada 5 minutos
        
        logger.info(f"🔄 Iniciando monitoreo de trailing stop multi-par con intervalo de {monitor_interval_minutes} minutos")
        
        while self.is_running:
            try:
                # Verificar trailing stop para todos los pares activos
                results = await self.multi_pair_manager.check_trailing_stop_for_all_pairs()
                
                successful_pairs = [pair for pair, success in results.items() if success]
                failed_pairs = [pair for pair, success in results.items() if not success]
                
                if successful_pairs:
                    logger.debug(f"✅ Trailing stop verificado para: {', '.join(successful_pairs)}")
                if failed_pairs:
                    logger.warning(f"⚠️ Error en trailing stop para: {', '.join(failed_pairs)}")
                
            except asyncio.CancelledError:
                logger.info("🛑 Monitoreo de trailing stop cancelado")
                break
            except Exception as e:
                logger.error(f"❌ Error en monitoreo de trailing stop: {str(e)}", exc_info=True)
                await self.notification_service.send_error_notification(
                    f"Error en monitoreo de trailing stop: {str(e)}",
                    {"timestamp": datetime.utcnow().isoformat()}
                )
            
            # Esperar hasta el próximo monitoreo
            if self.is_running:
                logger.debug(f"⏰ Esperando {monitor_interval_minutes} minutos hasta el próximo monitoreo")
                await asyncio.sleep(monitor_interval_minutes * 60)
    
    async def _config_reload_loop(self) -> None:
        """Loop de recarga de configuraciones cada 30 minutos."""
        reload_interval_minutes = 30  # Recarga cada 30 minutos
        
        logger.info(f"🔄 Iniciando recarga de configuraciones con intervalo de {reload_interval_minutes} minutos")
        
        while self.is_running:
            try:
                # Recargar configuraciones desde la base de datos
                await self.multi_pair_manager.reload_configs()
                
            except asyncio.CancelledError:
                logger.info("🛑 Recarga de configuraciones cancelada")
                break
            except Exception as e:
                logger.error(f"❌ Error en recarga de configuraciones: {str(e)}", exc_info=True)
            
            # Esperar hasta la próxima recarga
            if self.is_running:
                logger.debug(f"⏰ Esperando {reload_interval_minutes} minutos hasta la próxima recarga")
                await asyncio.sleep(reload_interval_minutes * 60)
    
    def get_status(self) -> dict:
        """Obtiene el estado actual del servicio multi-par."""
        return {
            "is_running": self.is_running,
            "telegram_chat_id": self.telegram_chat_id,
            "multi_pair_status": self.multi_pair_manager.get_status(),
            "cycle_task_running": self.cycle_task is not None and not self.cycle_task.done(),
            "trailing_stop_task_running": self.trailing_stop_task is not None and not self.trailing_stop_task.done(),
            "config_reload_task_running": self.config_reload_task is not None and not self.config_reload_task.done(),
            "timestamp": datetime.utcnow().isoformat()
        } 