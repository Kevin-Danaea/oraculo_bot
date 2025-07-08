"""
Caso de Uso: Ciclo de Vida del Servicio
=======================================

Gestiona el ciclo de vida del servicio brain de forma estateless.
Solo ejecuta análisis cada hora sin mantener estado propio.
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
    Estateless: No mantiene estado propio, solo ejecuta análisis.
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
    
    async def start_service(self) -> Dict[str, Any]:
        """
        Inicia el servicio brain (estateless).
        
        Returns:
            Resultado del inicio
        """
        try:
            logger.info("🚀 Iniciando servicio brain (estateless)...")
            
            # Limpiar stop event
            self._stop_event.clear()
            
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
            Resultado de la parada
        """
        try:
            logger.info("🛑 Deteniendo servicio brain...")
            
            # Marcar para parada
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
        Obtiene información básica del servicio (estateless).
        
        Returns:
            Información básica del servicio
        """
        try:
            return {
                "status": "success",
                "service_type": "brain",
                "description": "Servicio de análisis de trading (estateless)",
                "analysis_task_active": self._analysis_task is not None and not self._analysis_task.done(),
                "stop_event_set": self._stop_event.is_set(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo información del servicio: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Error obteniendo información del servicio"
            }
    
    async def _analysis_loop(self):
        """
        Bucle principal de análisis que se ejecuta cada hora (estateless).
        """
        logger.info("🔄 Bucle de análisis iniciado (estateless)")
        
        # Importar configuración de análisis
        from config import ANALYSIS_INTERVAL
        
        # Ejecutar primer análisis inmediatamente
        logger.info("🚀 Ejecutando primer análisis al iniciar...")
        await self._execute_analysis_cycle()
        
        # Bucle principal
        while not self._stop_event.is_set():
            try:
                logger.info(f"⏳ Esperando {ANALYSIS_INTERVAL} segundos hasta el próximo ciclo...")
                await asyncio.wait_for(self._stop_event.wait(), timeout=ANALYSIS_INTERVAL)
            except asyncio.TimeoutError:
                logger.info("⏰ Timeout alcanzado, ejecutando próximo ciclo de análisis...")
                # Ejecutar análisis después del timeout
                await self._execute_analysis_cycle()
            if self._stop_event.is_set():
                logger.info("🛑 Bucle de análisis detenido por solicitud")
                break
        
        logger.info("🔄 Bucle de análisis terminado")
    
    async def _execute_analysis_cycle(self):
        """
        Ejecuta un ciclo de análisis completo (estateless).
        """
        try:
            current_time = datetime.utcnow()
            
            logger.info(f"🧠 ========== CICLO DE ANÁLISIS ==========")
            logger.info(f"⏰ Iniciado: {current_time}")
            
            # Ejecutar análisis batch real
            logger.info("📊 Ejecutando análisis batch...")
            result = await self.batch_analysis_use_case.execute()
            
            if result['status'] == 'completed':
                logger.info(f"✅ Análisis completado: {result['successful_pairs']} exitosos, {result['failed_pairs']} fallidos")
            else:
                logger.error(f"❌ Error en análisis batch: {result.get('error', 'Error desconocido')}")
            
            logger.info(f"✅ Ciclo de análisis completado")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo de análisis: {e}")
            await self.notification_service.notify_error(
                f"Error en ciclo de análisis: {e}"
            ) 