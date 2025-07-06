"""
Repositorio de Estado del Brain
==============================

Implementación concreta del repositorio de estado del brain.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..domain.interfaces import BrainStatusRepository
from ..domain.entities import BrainStatus, BotType

logger = logging.getLogger(__name__)


class FileBrainStatusRepository(BrainStatusRepository):
    """
    Implementación del repositorio de estado usando archivos JSON.
    En el futuro, esto podría usar Redis o base de datos.
    """
    
    def __init__(self, status_file: str = "brain_status.json"):
        """
        Inicializa el repositorio.
        
        Args:
            status_file: Archivo para almacenar el estado
        """
        self.logger = logging.getLogger(__name__)
        self.status_file = Path(status_file)
        self._ensure_status_file()
    
    def _ensure_status_file(self):
        """Asegura que el archivo de estado existe."""
        try:
            if not self.status_file.exists():
                # Crear estado inicial
                initial_status = BrainStatus(
                    is_running=False,
                    cycle_count=0,
                    last_analysis_time=None,
                    supported_pairs=[],
                    active_bots=[BotType.GRID],
                    total_decisions_processed=0,
                    successful_decisions=0,
                    failed_decisions=0
                )
                self._save_status_to_file(initial_status)
                self.logger.info(f"✅ Archivo de estado creado: {self.status_file}")
        except Exception as e:
            self.logger.error(f"❌ Error creando archivo de estado: {e}")
    
    def _save_status_to_file(self, status: BrainStatus) -> bool:
        """
        Guarda el estado en el archivo JSON.
        
        Args:
            status: Estado a guardar
            
        Returns:
            True si se guardó correctamente
        """
        try:
            status_dict = status.to_dict()
            status_dict['_last_updated'] = datetime.utcnow().isoformat()
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_dict, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando estado en archivo: {e}")
            return False
    
    def _load_status_from_file(self) -> Optional[BrainStatus]:
        """
        Carga el estado desde el archivo JSON.
        
        Returns:
            Estado cargado o None si hay error
        """
        try:
            if not self.status_file.exists():
                return None
            
            with open(self.status_file, 'r', encoding='utf-8') as f:
                status_dict = json.load(f)
            
            # Convertir bot_types de strings a enums
            active_bots = []
            for bot_str in status_dict.get('active_bots', []):
                try:
                    active_bots.append(BotType(bot_str))
                except ValueError:
                    self.logger.warning(f"⚠️ Tipo de bot desconocido: {bot_str}")
            
            # Convertir last_analysis_time de string a datetime
            last_analysis_time = None
            if status_dict.get('last_analysis_time'):
                try:
                    last_analysis_time = datetime.fromisoformat(status_dict['last_analysis_time'])
                except ValueError:
                    self.logger.warning("⚠️ Formato de fecha inválido en last_analysis_time")
            
            status = BrainStatus(
                is_running=status_dict.get('is_running', False),
                cycle_count=status_dict.get('cycle_count', 0),
                last_analysis_time=last_analysis_time,
                supported_pairs=status_dict.get('supported_pairs', []),
                active_bots=active_bots,
                total_decisions_processed=status_dict.get('total_decisions_processed', 0),
                successful_decisions=status_dict.get('successful_decisions', 0),
                failed_decisions=status_dict.get('failed_decisions', 0)
            )
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando estado desde archivo: {e}")
            return None
    
    async def save_status(self, status: BrainStatus) -> bool:
        """
        Guarda el estado actual del brain.
        
        Args:
            status: Estado a guardar
            
        Returns:
            True si se guardó correctamente
        """
        try:
            success = self._save_status_to_file(status)
            if success:
                self.logger.debug(f"✅ Estado guardado: ciclo #{status.cycle_count}")
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando estado: {e}")
            return False
    
    async def get_status(self) -> Optional[BrainStatus]:
        """
        Obtiene el estado actual del brain.
        
        Returns:
            Estado actual o None si no existe
        """
        try:
            status = self._load_status_from_file()
            if status:
                self.logger.debug(f"✅ Estado cargado: ciclo #{status.cycle_count}")
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estado: {e}")
            return None
    
    async def update_cycle_count(self, cycle_count: int) -> bool:
        """
        Actualiza el contador de ciclos.
        
        Args:
            cycle_count: Nuevo contador de ciclos
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            current_status = await self.get_status()
            if current_status:
                updated_status = BrainStatus(
                    is_running=current_status.is_running,
                    cycle_count=cycle_count,
                    last_analysis_time=current_status.last_analysis_time,
                    supported_pairs=current_status.supported_pairs,
                    active_bots=current_status.active_bots,
                    total_decisions_processed=current_status.total_decisions_processed,
                    successful_decisions=current_status.successful_decisions,
                    failed_decisions=current_status.failed_decisions
                )
                return await self.save_status(updated_status)
            else:
                self.logger.warning("⚠️ No hay estado actual para actualizar")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando contador de ciclos: {e}")
            return False
    
    async def update_analysis_time(self, analysis_time: datetime) -> bool:
        """
        Actualiza el tiempo del último análisis.
        
        Args:
            analysis_time: Tiempo del análisis
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            current_status = await self.get_status()
            if current_status:
                updated_status = BrainStatus(
                    is_running=current_status.is_running,
                    cycle_count=current_status.cycle_count,
                    last_analysis_time=analysis_time,
                    supported_pairs=current_status.supported_pairs,
                    active_bots=current_status.active_bots,
                    total_decisions_processed=current_status.total_decisions_processed,
                    successful_decisions=current_status.successful_decisions,
                    failed_decisions=current_status.failed_decisions
                )
                return await self.save_status(updated_status)
            else:
                self.logger.warning("⚠️ No hay estado actual para actualizar")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando tiempo de análisis: {e}")
            return False
    
    async def update_decision_counts(
        self, 
        total_processed: int, 
        successful: int, 
        failed: int
    ) -> bool:
        """
        Actualiza los contadores de decisiones.
        
        Args:
            total_processed: Total de decisiones procesadas
            successful: Decisiones exitosas
            failed: Decisiones fallidas
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            current_status = await self.get_status()
            if current_status:
                updated_status = BrainStatus(
                    is_running=current_status.is_running,
                    cycle_count=current_status.cycle_count,
                    last_analysis_time=current_status.last_analysis_time,
                    supported_pairs=current_status.supported_pairs,
                    active_bots=current_status.active_bots,
                    total_decisions_processed=total_processed,
                    successful_decisions=successful,
                    failed_decisions=failed
                )
                return await self.save_status(updated_status)
            else:
                self.logger.warning("⚠️ No hay estado actual para actualizar")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando contadores de decisiones: {e}")
            return False
    
    async def reset_status(self) -> bool:
        """
        Resetea el estado del brain a valores iniciales.
        
        Returns:
            True si se reseteó correctamente
        """
        try:
            reset_status = BrainStatus(
                is_running=False,
                cycle_count=0,
                last_analysis_time=None,
                supported_pairs=[],
                active_bots=[BotType.GRID],
                total_decisions_processed=0,
                successful_decisions=0,
                failed_decisions=0
            )
            
            success = await self.save_status(reset_status)
            if success:
                self.logger.info("✅ Estado del brain reseteado")
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error reseteando estado: {e}")
            return False


class RedisBrainStatusRepository(BrainStatusRepository):
    """
    Implementación futura del repositorio de estado usando Redis.
    Esta clase está preparada para cuando se implemente Redis.
    """
    
    def __init__(self):
        """Inicializa el repositorio con Redis."""
        self.logger = logging.getLogger(__name__)
        self._redis_client = None
        # TODO: Implementar conexión a Redis
    
    async def save_status(self, status: BrainStatus) -> bool:
        """
        Guarda el estado en Redis.
        
        Args:
            status: Estado a guardar
            
        Returns:
            True si se guardó correctamente
        """
        # TODO: Implementar guardado en Redis
        self.logger.info(f"🔄 Guardado en Redis (futuro): ciclo #{status.cycle_count}")
        return True
    
    async def get_status(self) -> Optional[BrainStatus]:
        """
        Obtiene el estado desde Redis.
        
        Returns:
            Estado actual o None si no existe
        """
        # TODO: Implementar lectura desde Redis
        self.logger.info("🔄 Lectura desde Redis (futuro)")
        return None
    
    async def update_cycle_count(self, cycle_count: int) -> bool:
        """
        Actualiza el contador de ciclos en Redis.
        
        Args:
            cycle_count: Nuevo contador de ciclos
            
        Returns:
            True si se actualizó correctamente
        """
        # TODO: Implementar actualización en Redis
        self.logger.info(f"🔄 Actualización en Redis (futuro): ciclo #{cycle_count}")
        return True 