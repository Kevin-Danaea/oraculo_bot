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
from .domain.entities import TrendBotConfig
from .application.service_lifecycle_use_case import ServiceLifecycleUseCase
from .infrastructure.brain_directive_repository import DatabaseBrainDirectiveRepository
from .infrastructure.exchange_service import ExchangeService
from .infrastructure.notification_service import NotificationService
from .infrastructure.trend_bot_repository import JsonTrendBotRepository
from .infrastructure.state_manager import TrendBotStateManager

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
            logger.info("🚀 Inicializando Trend Following Bot...")
            
            # Configurar logging
            setup_logging()
            
            # Crear configuración del bot
            bot_config = TrendBotConfig(
                symbol=self.config.symbol,
                capital_allocation=self.config.capital_allocation,
                trailing_stop_percent=self.config.trailing_stop_percent,
                sandbox_mode=self.config.binance_testnet
            )
            
            # Inicializar servicios de infraestructura
            repository = JsonTrendBotRepository()
            brain_repository = DatabaseBrainDirectiveRepository()
            exchange_service = ExchangeService()
            notification_service = NotificationService()
            state_manager = TrendBotStateManager(repository)
            
            # Inicializar caso de uso del ciclo de vida
            self.lifecycle_use_case = ServiceLifecycleUseCase(
                repository=repository,
                brain_repository=brain_repository,
                exchange_service=exchange_service,
                notification_service=notification_service,
                state_manager=state_manager,
                config=bot_config
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