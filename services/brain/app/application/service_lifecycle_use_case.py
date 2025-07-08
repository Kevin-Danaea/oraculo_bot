"""
Caso de Uso: Ciclo de Vida del Servicio
=======================================

Gestiona el ciclo de vida del servicio brain, incluyendo inicio, parada y monitoreo.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.domain.interfaces import NotificationService
from app.application.batch_analysis_use_case import BatchAnalysisUseCase

logger = logging.getLogger(__name__)


class ServiceLifecycleUseCase:
    """
    Caso de uso para gestionar el ciclo de vida del servicio brain.
    """
    
    def __init__(
        self,
        notification_service: NotificationService,
        batch_analysis_use_case: BatchAnalysisUseCase
    ):
        """
        Inicializa el caso de uso.
        
        Args:
            notification_service: Servicio de notificaciones
            batch_analysis_use_case: Caso de uso para análisis batch
        """
        self.notification_service = notification_service
        self.batch_analysis_use_case = batch_analysis_use_case
        self._analysis_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_running = False
        self._cycle_count = 0
        self._last_analysis_time: Optional[datetime] = None
    
    async def start_service(self) -> Dict[str, Any]:
        """
        Inicia el servicio brain.
        
        Returns:
            Estado del servicio después del inicio
        """
        try:
            if self._is_running:
                logger.warning("⚠️ El servicio brain ya está ejecutándose")
                return {
                    "status": "already_running",
                    "message": "El servicio brain ya está ejecutándose"
                }
            
            logger.info("🚀 Iniciando servicio brain...")
            
            # Marcar como ejecutándose
            self._is_running = True
            self._stop_event.clear()
            self._cycle_count = 0
            self._last_analysis_time = None
            
            # Iniciar bucle de análisis en segundo plano
            self._analysis_task = asyncio.create_task(self._analysis_loop())
            
            logger.info("✅ Servicio brain iniciado correctamente")
            
            return {
                "status": "started",
                "message": "Servicio brain iniciado correctamente"
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
            
            logger.info("✅ Servicio brain detenido correctamente")
            
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
            return {
                "status": "success",
                "is_running": self._is_running,
                "cycle_count": self._cycle_count,
                "last_analysis_time": self._last_analysis_time.isoformat() if self._last_analysis_time else None,
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
        
        # Bucle principal
        while self._is_running and not self._stop_event.is_set():
            try:
                # Esperar hasta el próximo ciclo o hasta que se solicite parada
                await asyncio.wait_for(self._stop_event.wait(), timeout=ANALYSIS_INTERVAL)
                
                if self._stop_event.is_set():
                    logger.info("🛑 Bucle de análisis detenido por solicitud")
                    break
                
                # Ejecutar análisis
                await self._execute_analysis_cycle()
                
            except asyncio.TimeoutError:
                # Timeout normal, continuar con el siguiente ciclo
                continue
            except Exception as e:
                logger.error(f"❌ Error en bucle de análisis: {e}")
                await self.notification_service.notify_error(
                    f"Error en bucle de análisis: {e}",
                    {"cycle_count": self._cycle_count}
                )
                # Esperar un poco antes de continuar
                await asyncio.sleep(60)
        
        logger.info("🔄 Bucle de análisis terminado")
    
    async def _execute_analysis_cycle(self):
        """
        Ejecuta un ciclo de análisis completo.
        """
        try:
            self._cycle_count += 1
            self._last_analysis_time = datetime.utcnow()
            
            logger.info(f"🧠 ========== CICLO DE ANÁLISIS #{self._cycle_count} ==========")
            logger.info(f"⏰ Iniciado: {self._last_analysis_time}")
            
            # Ejecutar análisis batch real
            logger.info("📊 Ejecutando análisis batch...")
            result = await self.batch_analysis_use_case.execute()
            
            if result['status'] == 'completed':
                logger.info(f"✅ Análisis completado: {result['successful_pairs']} exitosos, {result['failed_pairs']} fallidos")
            else:
                logger.error(f"❌ Error en análisis batch: {result.get('error', 'Error desconocido')}")
            
            logger.info(f"✅ Ciclo #{self._cycle_count} completado")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo #{self._cycle_count}: {e}")
            await self.notification_service.notify_error(
                f"Error en ciclo de análisis #{self._cycle_count}: {e}"
            )
    
    def is_running(self) -> bool:
        """
        Verifica si el servicio está ejecutándose.
        
        Returns:
            True si está ejecutándose
        """
        return self._is_running 