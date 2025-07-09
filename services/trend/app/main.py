"""Main entry point for Trend Following Bot service."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from shared.services.logging_config import setup_logging
from .config import get_config
from .application.service_lifecycle_use_case import ServiceLifecycleUseCase
from .infrastructure.exchange_service import ExchangeService
from .infrastructure.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TrendBotService:
    """Servicio principal del Trend Following Bot."""
    
    def __init__(self):
        self.config = get_config()
        self.lifecycle_use_case = None
        self.running = False
        
    async def initialize(self):
        """Inicializa todas las dependencias del servicio."""
        try:
            logger.info("Inicializando Trend Following Bot...")
            
            # Configurar logging
            setup_logging()
            
            # Inicializar servicios de infraestructura
            exchange_service = ExchangeService()
            notification_service = NotificationService()
            
            # TODO: Inicializar otros adaptadores cuando estén listos
            # trend_analyzer = TrendAnalyzer()
            # position_manager = PositionManager()
            # repository = TrendRepository()
            # risk_manager = RiskManager()
            
            # TODO: Inicializar casos de uso
            # analyze_market_use_case = AnalyzeMarketUseCase(...)
            # execute_trades_use_case = ExecuteTradesUseCase(...)
            # manage_positions_use_case = ManagePositionsUseCase(...)
            
            # Por ahora solo configuramos el lifecycle
            self.lifecycle_use_case = ServiceLifecycleUseCase(
                analyze_market_use_case=None,  # TODO: implementar
                execute_trades_use_case=None,  # TODO: implementar
                manage_positions_use_case=None,  # TODO: implementar
                notification_service=notification_service,
                repository=None  # TODO: implementar
            )
            
            logger.info("✅ Trend Following Bot inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio: {str(e)}", exc_info=True)
            raise
    
    async def start(self):
        """Inicia el servicio."""
        try:
            if not self.lifecycle_use_case:
                await self.initialize()
            
            logger.info("🚀 Iniciando Trend Following Bot...")
            self.running = True
            
            # Configurar manejadores de señales
            self._setup_signal_handlers()
            
            # Iniciar el ciclo de vida del servicio
            if self.lifecycle_use_case:
                await self.lifecycle_use_case.start()
            
            # Mantener el servicio corriendo
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupción manual detectada")
        except Exception as e:
            logger.error(f"Error ejecutando servicio: {str(e)}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """Detiene el servicio."""
        try:
            logger.info("🛑 Deteniendo Trend Following Bot...")
            self.running = False
            
            if self.lifecycle_use_case:
                await self.lifecycle_use_case.stop()
            
            logger.info("✅ Trend Following Bot detenido correctamente")
            
        except Exception as e:
            logger.error(f"Error deteniendo servicio: {str(e)}", exc_info=True)
    
    def _setup_signal_handlers(self):
        """Configura los manejadores de señales del sistema."""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Deteniendo servicio...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Función principal."""
    service = TrendBotService()
    await service.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Servicio detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1) 