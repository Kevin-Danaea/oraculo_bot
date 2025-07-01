"""
Cerebro Service Layer
=====================

This module contains the main service class that orchestrates the
Cerebro's logic, including the analysis loop.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from .core.decision_engine import DecisionEngine
from .core.multibot_notifier import get_multibot_notifier
from .core.recipe_master import PARES_A_MONITOREAR
from .core.settings import INTERVALO_ANALISIS


class CerebroService:
    """
    The main service class for Cerebro.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.decision_engine = DecisionEngine()
        self.notifier = get_multibot_notifier()
        self.is_running = False
        self.analysis_task: Optional[asyncio.Task] = None
        self.previous_decisions: Dict[str, str] = {}
        self.grid_is_connected = False
        self.last_batch_result: Optional[Dict] = None
        self.last_batch_timestamp: Optional[datetime] = None

    async def start(self):
        """Starts the main analysis loop."""
        if self.is_running:
            self.logger.warning("⚠️ El bucle de análisis ya está activo")
            return

        self.is_running = True
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        self.logger.info("🚀 Bucle de análisis iniciado")

    async def stop(self):
        """Stops the main analysis loop."""
        if not self.is_running:
            self.logger.warning("⚠️ El bucle de análisis no está activo")
            return

        self.is_running = False
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                self.logger.info("Bucle de análisis cancelado correctamente.")
        self.logger.info("🛑 Bucle de análisis detenido")

    def get_status(self):
        return {
            "is_running": self.is_running,
            "grid_is_connected": self.grid_is_connected,
            "last_batch_timestamp": self.last_batch_timestamp,
            "monitored_pairs": PARES_A_MONITOREAR
        }

    async def _analysis_loop(self):
        """
        The main loop that runs the continuous analysis of the monitored pairs.
        """
        self.logger.info("🚀 ========== INICIANDO BUCLE PRINCIPAL DE ANÁLISIS MULTIBOT BATCH ==========")
        self.logger.info(f"📊 Pares a monitorear: {PARES_A_MONITOREAR}")
        self.logger.info(f"⏰ Intervalo de análisis: {INTERVALO_ANALISIS} segundos")
        
        cycle_count = 0
        while self.is_running:
            try:
                cycle_count += 1
                self.logger.info(f"🔄 ========== INICIANDO CICLO BATCH #{cycle_count} ==========")
                
                batch_results = self.decision_engine.analizar_todos_los_pares()
                self.last_batch_result = batch_results
                self.last_batch_timestamp = datetime.now()

                if not batch_results:
                    self.logger.error("❌ Error en análisis batch - no se obtuvieron resultados")
                    await asyncio.sleep(60) # Wait before retrying
                    continue

                await self._process_batch_results(batch_results)

                self.logger.info(f"✅ ========== CICLO BATCH #{cycle_count} COMPLETADO ==========")
                
                if self.is_running:
                    self.logger.info(f"⏳ Esperando {INTERVALO_ANALISIS} segundos hasta el próximo ciclo...")
                    await asyncio.sleep(INTERVALO_ANALISIS)

            except Exception as e:
                self.logger.error(f"💥 Error crítico en bucle principal batch: {str(e)}")
                self.logger.info("🔄 Reintentando en 60 segundos...")
                if self.is_running:
                    await asyncio.sleep(60)

    async def _process_batch_results(self, batch_results: Dict[str, Any]):
        """Processes the results of a batch analysis, detecting and notifying changes."""
        changes_detected = {}
        for pair, result in batch_results.items():
            if not self.is_running:
                break
            
            if result.get('success', False):
                current_decision = result['decision']
                previous_decision = self.previous_decisions.get(pair)

                if previous_decision != current_decision:
                    self.logger.info(f"🔄 CAMBIO DETECTADO en {pair}: {previous_decision or 'N/A'} -> {current_decision}")
                    changes_detected[pair] = {
                        'decision': current_decision,
                        'razon': result['razon'],
                        'indicadores': result['indicadores']
                    }
                    self.previous_decisions[pair] = current_decision
                else:
                    self.logger.info(f"➡️ {pair}: Sin cambios ({current_decision})")
            else:
                self.logger.error(f"❌ Error en análisis de {pair}: {result.get('error', 'Error desconocido')}")
        
        if changes_detected:
            self.logger.info(f"📢 Notificando {len(changes_detected)} cambios al Grid...")
            try:
                notification_results = await self.notifier.notify_all_decisions(changes_detected)
                successful_notifications = sum(1 for success in notification_results.values() if success)
                self.logger.info(f"✅ Notificaciones enviadas: {successful_notifications}/{len(changes_detected)} exitosas")
            except Exception as e:
                self.logger.error(f"❌ Error en notificación batch: {e}")
        else:
            self.logger.info("ℹ️ No se detectaron cambios - no se envían notificaciones")
    
    async def analyze_pair_for_grid_startup(self, pair: str) -> Dict[str, Any]:
        """
        Handles the initial request from the Grid service for a specific pair.
        This triggers the start of the continuous monitoring loop if it's the first connection.
        """
        if not self.grid_is_connected:
            self.logger.info("🚀 ========== PRIMERA CONEXIÓN DEL GRID DETECTADA ==========")
            self.grid_is_connected = True
            # The loop is started from the lifespan manager now
        
        result = self.decision_engine.analizar_par(pair)
        if not result.get('success', False):
            raise Exception(f"Error analizando {pair}: {result.get('error', 'Error desconocido')}")
        
        # Update previous decision to avoid immediate re-notification
        self.previous_decisions[pair] = result['decision']
        
        return {
            "par": pair,
            "decision": result['decision'],
            "razon": result['razon'],
            "timestamp": datetime.now().isoformat(),
            "puede_operar": result['decision'] == "OPERAR_GRID",
            "fuente": "cerebro_primera_conexion" if self.grid_is_connected else "cerebro_consulta_posterior",
            "monitoreo_activado": self.is_running
        }

    async def get_batch_analysis(self, force: bool = False) -> Dict[str, Any]:
        """
        Gets the batch analysis for all pairs.
        If force=true, runs a new analysis. Otherwise, returns the last cached result.
        """
        if force or self.last_batch_result is None:
            self.logger.info("🚀 Ejecutando análisis batch (forzado o primer uso)...")
            batch_results = self.decision_engine.analizar_todos_los_pares()
            self.last_batch_result = batch_results
            self.last_batch_timestamp = datetime.now()
        else:
            self.logger.info(f"ℹ️ Devolviendo resultado batch cacheado (timestamp: {self.last_batch_timestamp})")
            batch_results = self.last_batch_result

        if not batch_results:
            raise Exception("Error ejecutando análisis batch")
        
        return self._format_batch_response(batch_results)

    def _format_batch_response(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Formats the batch analysis result into a response dictionary."""
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "batch_cached_at": self.last_batch_timestamp.isoformat() if self.last_batch_timestamp else None,
            "total_pairs": len(batch_results),
            "pairs_analyzed": list(batch_results.keys()),
            "results": {},
            "summary": {
                "OPERAR_GRID": 0,
                "PAUSAR_GRID": 0,
                "ERROR": 0
            }
        }
        for par, resultado in batch_results.items():
            response["results"][par] = resultado
            if resultado.get('success', False):
                decision = resultado.get('decision', 'ERROR')
                response["summary"][decision] += 1
            else:
                response["summary"]["ERROR"] += 1
        
        self.logger.info(f"✅ Análisis batch entregado: {response['summary']}")
        return response 