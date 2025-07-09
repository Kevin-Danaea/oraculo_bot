"""Use case for managing the trend bot service lifecycle."""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceLifecycleUseCase:
    """Caso de uso para gestionar el ciclo de vida del servicio trend bot."""
    
    def __init__(
        self,
        analyze_market_use_case,
        execute_trades_use_case,
        manage_positions_use_case,
        notification_service,
        repository
    ):
        self.analyze_market_use_case = analyze_market_use_case
        self.execute_trades_use_case = execute_trades_use_case
        self.manage_positions_use_case = manage_positions_use_case
        self.notification_service = notification_service
        self.repository = repository
        
        self.is_running = False
        self.tasks = []
        
    async def start(self) -> None:
        """Inicia el servicio y sus tareas programadas."""
        if self.is_running:
            logger.warning("El servicio ya está en ejecución")
            return
            
        logger.info("Iniciando servicio Trend Following Bot...")
        self.is_running = True
        
        try:
            # Notificar inicio
            await self.notification_service.send_error_alert(
                "🚀 Trend Following Bot iniciado",
                {"timestamp": datetime.utcnow().isoformat()}
            )
            
            # Iniciar tareas principales
            self.tasks = [
                asyncio.create_task(self._market_analysis_loop()),
                asyncio.create_task(self._trade_execution_loop()),
                asyncio.create_task(self._position_management_loop()),
                asyncio.create_task(self._daily_summary_task()),
                asyncio.create_task(self._health_check_loop())
            ]
            
            logger.info("Todas las tareas del servicio han sido iniciadas")
            
        except Exception as e:
            logger.error(f"Error iniciando servicio: {str(e)}", exc_info=True)
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """Detiene el servicio y cancela todas las tareas."""
        if not self.is_running:
            logger.warning("El servicio no está en ejecución")
            return
            
        logger.info("Deteniendo servicio Trend Following Bot...")
        self.is_running = False
        
        # Cancelar todas las tareas
        for task in self.tasks:
            task.cancel()
            
        # Esperar a que todas las tareas terminen
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Notificar detención
        await self.notification_service.send_error_alert(
            "🛑 Trend Following Bot detenido",
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        logger.info("Servicio detenido exitosamente")
    
    async def _market_analysis_loop(self) -> None:
        """Loop principal para análisis de mercado."""
        interval_minutes = 15  # Analizar cada 15 minutos
        
        while self.is_running:
            try:
                logger.debug("Ejecutando análisis de mercado...")
                signals = await self.analyze_market_use_case.execute()
                
                if signals:
                    logger.info(f"Se generaron {len(signals)} nuevas señales")
                
            except Exception as e:
                logger.error(
                    f"Error en loop de análisis de mercado: {str(e)}",
                    exc_info=True
                )
                
            # Esperar hasta el próximo ciclo
            await asyncio.sleep(interval_minutes * 60)
    
    async def _trade_execution_loop(self) -> None:
        """Loop principal para ejecución de trades."""
        interval_minutes = 5  # Verificar señales cada 5 minutos
        
        while self.is_running:
            try:
                logger.debug("Verificando señales para ejecutar trades...")
                trades_executed = await self.execute_trades_use_case.execute()
                
                if trades_executed > 0:
                    logger.info(f"Se ejecutaron {trades_executed} trades")
                
            except Exception as e:
                logger.error(
                    f"Error en loop de ejecución de trades: {str(e)}",
                    exc_info=True
                )
                
            # Esperar hasta el próximo ciclo
            await asyncio.sleep(interval_minutes * 60)
    
    async def _position_management_loop(self) -> None:
        """Loop principal para gestión de posiciones."""
        interval_minutes = 2  # Gestionar posiciones cada 2 minutos
        
        while self.is_running:
            try:
                logger.debug("Gestionando posiciones abiertas...")
                positions_processed = await self.manage_positions_use_case.execute()
                
                if positions_processed > 0:
                    logger.debug(f"Se procesaron {positions_processed} posiciones")
                
            except Exception as e:
                logger.error(
                    f"Error en loop de gestión de posiciones: {str(e)}",
                    exc_info=True
                )
                
            # Esperar hasta el próximo ciclo
            await asyncio.sleep(interval_minutes * 60)
    
    async def _daily_summary_task(self) -> None:
        """Tarea para enviar resumen diario."""
        summary_time = time(12, 0)  # 12:00 PM UTC
        
        while self.is_running:
            try:
                now = datetime.utcnow()
                
                # Calcular tiempo hasta el próximo resumen
                next_summary = now.replace(
                    hour=summary_time.hour,
                    minute=summary_time.minute,
                    second=0,
                    microsecond=0
                )
                
                if now >= next_summary:
                    # Si ya pasó la hora, programar para mañana
                    next_summary = next_summary.replace(day=next_summary.day + 1)
                
                wait_seconds = (next_summary - now).total_seconds()
                logger.info(
                    f"Próximo resumen diario en {wait_seconds/3600:.1f} horas"
                )
                
                # Esperar hasta la hora del resumen
                await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._send_daily_summary()
                
            except Exception as e:
                logger.error(
                    f"Error en tarea de resumen diario: {str(e)}",
                    exc_info=True
                )
                # En caso de error, esperar 1 hora antes de reintentar
                await asyncio.sleep(3600)
    
    async def _send_daily_summary(self) -> None:
        """Envía el resumen diario de rendimiento."""
        try:
            # Obtener todas las estrategias
            strategies = await self.repository.get_all_strategies(enabled_only=False)
            
            for strategy in strategies:
                # Obtener métricas
                metrics = await self.repository.get_metrics(strategy.symbol)
                
                if metrics and metrics.total_trades > 0:
                    # Obtener posiciones del día
                    all_positions = await self.repository.get_open_positions(strategy.symbol)
                    
                    # Enviar resumen
                    await self.notification_service.send_daily_summary(
                        metrics, all_positions
                    )
                    
            logger.info("Resumen diario enviado exitosamente")
            
        except Exception as e:
            logger.error(
                f"Error enviando resumen diario: {str(e)}",
                exc_info=True
            )
    
    async def _health_check_loop(self) -> None:
        """Loop para verificar la salud del servicio."""
        interval_minutes = 30  # Verificar cada 30 minutos
        
        while self.is_running:
            try:
                # Verificar conexión con exchange
                strategies = await self.repository.get_all_strategies(enabled_only=True)
                
                if strategies:
                    # Intentar obtener precio de un símbolo
                    test_symbol = strategies[0].symbol
                    # TODO: Implementar cuando ExchangeService esté disponible
                    # from ..infrastructure.exchange_service import ExchangeService
                    # exchange = ExchangeService()
                    # price = await exchange.get_current_price(test_symbol)
                    price = None  # Temporal
                    
                    if price:
                        logger.debug(f"Health check OK - Precio {test_symbol}: {price}")
                    else:
                        logger.warning("Health check: No se pudo obtener precio")
                        await self.notification_service.send_error_alert(
                            "⚠️ Health check falló",
                            {"reason": "No se pudo obtener precio del exchange"}
                        )
                
            except Exception as e:
                logger.error(
                    f"Error en health check: {str(e)}",
                    exc_info=True
                )
                await self.notification_service.send_error_alert(
                    "❌ Health check crítico",
                    {"error": str(e)}
                )
                
            # Esperar hasta el próximo ciclo
            await asyncio.sleep(interval_minutes * 60)
    
    def get_status(self) -> dict:
        """Obtiene el estado actual del servicio."""
        return {
            "is_running": self.is_running,
            "active_tasks": len([t for t in self.tasks if not t.done()]),
            "total_tasks": len(self.tasks),
            "timestamp": datetime.utcnow().isoformat()
        } 