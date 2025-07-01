"""
Cerebro Service Layer
=====================

This module contains the main service class that orchestrates the
Cerebro's logic, including the analysis loop.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any

from .core.settings import INTERVALO_ANALISIS
from .core.decision_engine import DecisionEngine
from .core.multibot_notifier import get_multibot_notifier
from .core.recipe_master import PARES_A_MONITOREAR

logger = logging.getLogger(__name__)


class CerebroService:
    """
    Servicio que gestiona el ciclo de vida del análisis del cerebro.
    """
    def __init__(self):
        self._analysis_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_running = False
        self.grid_is_connected = False
        self.decision_engine = DecisionEngine()
        self._last_batch_analysis: Dict[str, Any] = {}
        self._last_analysis_time: Optional[datetime] = None
        self._previous_decisions: Dict[str, str] = {}
        self.cycle_count = 1

    async def start(self) -> Dict[str, Any]:
        """
        Inicia el servicio: ejecuta el primer análisis y luego el bucle.
        """
        if self._is_running:
            logger.warning("⚠️ Se intentó iniciar Cerebro, pero ya estaba activo.")
            return self._last_batch_analysis

        logger.info("🚀 Iniciando servicio Cerebro: Realizando primer análisis batch...")
        self._is_running = True
        self.grid_is_connected = True
        self._stop_event.clear()

        # 1. Ejecutar el primer análisis
        batch_results = self.decision_engine.analizar_todos_los_pares()
        self._last_batch_analysis = self._format_batch_response(batch_results)
        self._last_analysis_time = datetime.now()

        # 2. Procesar y notificar los resultados iniciales
        await self._process_batch_results(batch_results)
        
        # 3. Iniciar el bucle de fondo
        self._analysis_task = asyncio.create_task(self._analysis_loop())
        logger.info("✅ Primer análisis completado. Bucle de fondo iniciado.")

        return self._last_batch_analysis

    async def stop(self):
        """Detiene el bucle de análisis de forma segura."""
        if self._is_running:
            self._is_running = False
            self._stop_event.set()
            if self._analysis_task:
                try:
                    await asyncio.wait_for(self._analysis_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._analysis_task.cancel()
                    logger.warning("⚠️ El bucle de análisis no respondió, fue forzado a detenerse.")
            logger.info("✅ Bucle de análisis detenido.")
        else:
            logger.warning("⚠️ El bucle de análisis no está activo")

    def get_status(self) -> Dict[str, Any]:
        return {
            'is_running': self._is_running,
            'grid_is_connected': self.grid_is_connected,
            'cycle_count': self.cycle_count
        }

    def is_running(self) -> bool:
        return self._is_running

    async def _analysis_loop(self):
        """
        Bucle que ejecuta el análisis periódicamente.
        Espera el intervalo ANTES de ejecutar el ciclo.
        """
        logger.info("🚀 Bucle de análisis en segundo plano iniciado.")
        
        while not self._stop_event.is_set():
            try:
                logger.info(f"⏳ Esperando {INTERVALO_ANALISIS} segundos para el próximo ciclo...")
                await asyncio.sleep(INTERVALO_ANALISIS)

                if self._stop_event.is_set():
                    break

                self.cycle_count += 1
                logger.info(f"🔄 ========== INICIANDO CICLO BATCH #{self.cycle_count} ==========")
                
                batch_results = self.decision_engine.analizar_todos_los_pares()
                self._last_batch_analysis = self._format_batch_response(batch_results)
                self._last_analysis_time = datetime.now()
                
                await self._process_batch_results(batch_results)
                
                logger.info(f"✅ ========== CICLO BATCH #{self.cycle_count -1} COMPLETADO ==========")

            except asyncio.CancelledError:
                logger.info("🛑 Bucle de análisis cancelado.")
                break
            except Exception as e:
                logger.error(f"❌ Error en el bucle de análisis: {e}")
                await asyncio.sleep(60)
                
    async def _process_batch_results(self, batch_results: Dict[str, Any]):
        """Compara resultados con decisiones previas y notifica cambios."""
        changes_detected = []
        
        for par, result in batch_results.items():
            if not result.get('success'):
                continue
            
            new_decision = result.get('decision')
            previous_decision = self._previous_decisions.get(par)
            
            if new_decision != previous_decision:
                logger.info(f"🔄 CAMBIO DETECTADO en {par}: {previous_decision} -> {new_decision}")
                changes_detected.append({
                    'par': par,
                    'decision': new_decision,
                    'razon': result.get('razon', ''),
                    'indicadores': result.get('indicadores', {})
                })
                self._previous_decisions[par] = new_decision

        if changes_detected:
            logger.info(f"📢 Notificando {len(changes_detected)} cambios al Grid...")
            notifier = get_multibot_notifier()
            tasks = [
                notifier.notify_grid_decision_change(
                    pair=change['par'],
                    decision=change['decision'],
                    razon=change['razon'],
                    indicadores=change['indicadores']
                ) for change in changes_detected
            ]
            results = await asyncio.gather(*tasks)
            successful_notifications = sum(1 for res in results if res)
            logger.info(f"✅ Notificaciones enviadas: {successful_notifications}/{len(changes_detected)} exitosas")
        else:
            logger.info("ℹ️ No se detectaron cambios en las decisiones. No se enviarán notificaciones.")

    async def analyze_pair_for_grid_startup(self, pair: str) -> Dict[str, Any]:
        """
        Analiza un solo par para la inicialización del Grid.
        Si el servicio no está corriendo, lo inicia.
        """
        if not self._is_running:
            await self.start()
        
        # Devuelve la parte relevante del último análisis batch
        if pair in self._last_batch_analysis.get('results', {}):
            return self._last_batch_analysis['results'][pair]
        else:
            # Si por alguna razón no está, analizarlo individualmente como fallback
            logger.warning(f"⚠️ Par {pair} no encontrado en análisis batch, ejecutando individualmente.")
            return self.decision_engine.analizar_par(pair)

    async def get_batch_analysis(self, force: bool = False) -> Dict[str, Any]:
        """
        Obtiene el análisis batch. Si force=True, lo ejecuta ahora.
        """
        if force or not self._last_batch_analysis:
            logger.info("🚀 Ejecutando análisis batch (forzado o primer uso)...")
            batch_results = self.decision_engine.analizar_todos_los_pares()
            self._last_batch_analysis = self._format_batch_response(batch_results)
            self._last_analysis_time = datetime.now()
        else:
            logger.info(f"ℹ️ Devolviendo resultado batch cacheado (timestamp: {self._last_analysis_time})")
        
        return self._last_batch_analysis

    def _format_batch_response(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea la respuesta del análisis batch."""
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "batch_cached_at": self._last_analysis_time.isoformat() if self._last_analysis_time else None,
            "total_pairs": len(batch_results),
            "pairs_analyzed": list(batch_results.keys()),
            "results": batch_results,
            "summary": {
                "OPERAR_GRID": 0,
                "PAUSAR_GRID": 0,
                "ERROR": 0
            }
        }
        
        for result in batch_results.values():
            decision = result.get('decision', 'ERROR')
            if decision in response["summary"]:
                response["summary"][decision] += 1
            else:
                response["summary"]["ERROR"] += 1
        
        logger.info(f"✅ Análisis batch entregado: {response['summary']}")
        return response 