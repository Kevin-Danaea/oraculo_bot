"""
Caso de Uso: Ciclo de Vida del Servicio
=======================================

Gestiona el ciclo de vida del servicio brain, incluyendo inicio, parada y monitoreo.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.domain.entities import BrainStatus, BotType
from app.domain.interfaces import BrainStatusRepository, NotificationService

logger = logging.getLogger(__name__)


class ServiceLifecycleUseCase:
    """
    Caso de uso para gestionar el ciclo de vida del servicio brain.
    """
    
    def __init__(
        self,
        status_repo: BrainStatusRepository,
        notification_service: NotificationService
    ):
        """
        Inicializa el caso de uso.
        
        Args:
            status_repo: Repositorio de estado del brain
            notification_service: Servicio de notificaciones
        """
        self.status_repo = status_repo
        self.notification_service = notification_service
        self._analysis_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_running = False
    
    async def start_service(self) -> Dict[str, Any]:
        """
        Inicia el servicio brain.
        
        Returns:
            Estado del servicio después del inicio
        """
        try:
            if self._is_running:
                logger.warning("⚠️ El servicio brain ya está ejecutándose")
                current_status = await self.status_repo.get_status()
                return {
                    "status": "already_running",
                    "message": "El servicio brain ya está ejecutándose",
                    "brain_status": current_status.to_dict() if current_status else None
                }
            
            logger.info("🚀 Iniciando servicio brain...")
            
            # Crear estado inicial
            initial_status = BrainStatus(
                is_running=True,
                cycle_count=0,
                last_analysis_time=None,
                supported_pairs=[],  # Se actualizará en el primer análisis
                active_bots=[BotType.GRID],
                total_decisions_processed=0,
                successful_decisions=0,
                failed_decisions=0
            )
            
            await self.status_repo.save_status(initial_status)
            
            # Marcar como ejecutándose
            self._is_running = True
            self._stop_event.clear()
            
            # Iniciar bucle de análisis en segundo plano
            self._analysis_task = asyncio.create_task(self._analysis_loop())
            
            logger.info("✅ Servicio brain iniciado correctamente")
            
            return {
                "status": "started",
                "message": "Servicio brain iniciado correctamente",
                "brain_status": initial_status.to_dict()
            }
            
        except Exception as e:
            logger.error(f"❌ Error iniciando servicio brain: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Error iniciando servicio brain"
            }
    
    async def stop_service(self) -> Dict[str, Any]:
        """
        Detiene el servicio brain.
        
        Returns:
            Estado del servicio después de la parada
        """
        try:
            if not self._is_running:
                logger.warning("⚠️ El servicio brain no está ejecutándose")
                return {
                    "status": "not_running",
                    "message": "El servicio brain no está ejecutándose"
                }
            
            logger.info("🛑 Deteniendo servicio brain...")
            
            # Marcar para parada
            self._is_running = False
            self._stop_event.set()
            
            # Esperar a que termine el bucle de análisis
            if self._analysis_task:
                try:
                    await asyncio.wait_for(self._analysis_task, timeout=10.0)
                except asyncio.TimeoutError:
                    self._analysis_task.cancel()
                    logger.warning("⚠️ El bucle de análisis no respondió, fue forzado a detenerse")
            
            # Actualizar estado
            current_status = await self.status_repo.get_status()
            if current_status:
                stopped_status = BrainStatus(
                    is_running=False,
                    cycle_count=current_status.cycle_count,
                    last_analysis_time=current_status.last_analysis_time,
                    supported_pairs=current_status.supported_pairs,
                    active_bots=current_status.active_bots,
                    total_decisions_processed=current_status.total_decisions_processed,
                    successful_decisions=current_status.successful_decisions,
                    failed_decisions=current_status.failed_decisions
                )
                await self.status_repo.save_status(stopped_status)
                
                logger.info("✅ Servicio brain detenido correctamente")
                
                return {
                    "status": "stopped",
                    "message": "Servicio brain detenido correctamente",
                    "brain_status": stopped_status.to_dict()
                }
            
            return {
                "status": "stopped",
                "message": "Servicio brain detenido correctamente"
            }
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo servicio brain: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Error deteniendo servicio brain"
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del servicio.
        
        Returns:
            Estado actual del servicio
        """
        try:
            current_status = await self.status_repo.get_status()
            
            return {
                "status": "success",
                "is_running": self._is_running,
                "brain_status": current_status.to_dict() if current_status else None,
                "analysis_task_active": self._analysis_task is not None and not self._analysis_task.done(),
                "stop_event_set": self._stop_event.is_set()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del servicio: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Error obteniendo estado del servicio"
            }
    
    async def _analysis_loop(self):
        """
        Bucle principal de análisis que se ejecuta cada hora.
        """
        logger.info("🔄 Bucle de análisis iniciado")
        
        # Intervalo de análisis (1 hora = 3600 segundos)
        ANALYSIS_INTERVAL = 3600
        
        # Ejecutar primer análisis inmediatamente
        logger.info("🚀 Ejecutando primer análisis al iniciar...")
        await self._execute_analysis_cycle()
        
        while not self._stop_event.is_set():
            try:
                logger.info(f"⏳ Esperando {ANALYSIS_INTERVAL} segundos para el próximo análisis...")
                await asyncio.sleep(ANALYSIS_INTERVAL)
                
                if self._stop_event.is_set():
                    break
                
                logger.info("🔄 Ejecutando análisis programado...")
                await self._execute_analysis_cycle()
                
            except asyncio.CancelledError:
                logger.info("🛑 Bucle de análisis cancelado")
                break
            except Exception as e:
                logger.error(f"❌ Error en el bucle de análisis: {e}")
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
        
        logger.info("🔄 Bucle de análisis terminado")
    
    async def _execute_analysis_cycle(self):
        """
        Ejecuta un ciclo de análisis completo.
        """
        try:
            # Obtener estado actual
            current_status = await self.status_repo.get_status()
            if current_status:
                new_cycle_count = current_status.cycle_count + 1
                
                # Actualizar estado con nuevo ciclo y tiempo de análisis
                updated_status = BrainStatus(
                    is_running=current_status.is_running,
                    cycle_count=new_cycle_count,
                    last_analysis_time=datetime.utcnow(),
                    supported_pairs=current_status.supported_pairs,
                    active_bots=current_status.active_bots,
                    total_decisions_processed=current_status.total_decisions_processed,
                    successful_decisions=current_status.successful_decisions,
                    failed_decisions=current_status.failed_decisions
                )
                
                # Guardar estado actualizado
                success = await self.status_repo.save_status(updated_status)
                if success:
                    logger.info(f"✅ Ciclo #{new_cycle_count} completado y guardado")
                else:
                    logger.error(f"❌ Error guardando estado del ciclo #{new_cycle_count}")
            else:
                logger.warning("⚠️ No se pudo obtener el estado actual para el análisis")
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo de análisis: {e}")
    
    def is_running(self) -> bool:
        """
        Verifica si el servicio está ejecutándose.
        
        Returns:
            True si el servicio está ejecutándose
        """
        return self._is_running 