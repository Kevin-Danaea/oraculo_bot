"""
Bot de Telegram simplificado para comandos básicos del Grid Trading.
"""
from typing import Optional

from shared.services.telegram_trading import TelegramTradingService
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

class GridTelegramBot:
    """Bot de Telegram simplificado para control básico del Grid Trading."""
    
    def __init__(self, scheduler_instance):
        """Inicializa el bot de Telegram."""
        self.scheduler = scheduler_instance
        self.telegram_service = TelegramTradingService()
        self.is_active = False
        logger.info("✅ GridTelegramBot inicializado")

    def start(self):
        """Marca el bot como activo."""
        self.is_active = True
        logger.info("✅ Bot de Telegram activado")
        return True

    def stop(self):
        """Marca el bot como inactivo."""
        self.is_active = False
        logger.info("✅ Bot de Telegram desactivado")

    def send_message(self, message: str):
        """Envía un mensaje por Telegram."""
        try:
            return self.telegram_service.send_message(message)
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            return False

    def handle_command(self, command: str) -> str:
        """Maneja comandos básicos del Grid Trading."""
        try:
            command = command.lower().strip()
            
            if command == "start_bot":
                return self._handle_start_bot()
            elif command == "stop_bot":
                return self._handle_stop_bot()
            elif command == "status":
                return self._handle_status()
            elif command == "sandbox":
                return self._handle_sandbox()
            elif command in ["production", "production confirm"]:
                return self._handle_production(command)
            elif command == "monitor":
                return self._handle_manual_monitor()
            else:
                return (
                    "🤖 <b>Comandos disponibles:</b>\n\n"
                    "• <code>start_bot</code> - Iniciar Grid Trading\n"
                    "• <code>stop_bot</code> - Detener Grid Trading\n"
                    "• <code>status</code> - Ver estado del sistema\n"
                    "• <code>sandbox</code> - Cambiar a modo pruebas\n"
                    "• <code>production</code> - Cambiar a modo real\n"
                    "• <code>monitor</code> - Ejecutar monitoreo manual"
                )
                
        except Exception as e:
            logger.error(f"❌ Error procesando comando {command}: {e}")
            return f"❌ Error procesando comando: {str(e)}"

    def _handle_start_bot(self) -> str:
        """Maneja el comando start_bot."""
        try:
            if not self.scheduler:
                return "❌ Scheduler no disponible"
            
            if self.scheduler.is_running():
                return "✅ Grid Trading ya está ejecutándose"
            
            self.scheduler.start()
            return "🚀 Grid Trading iniciado correctamente"
            
        except Exception as e:
            return f"❌ Error iniciando Grid Trading: {str(e)}"

    def _handle_stop_bot(self) -> str:
        """Maneja el comando stop_bot."""
        try:
            if not self.scheduler:
                return "❌ Scheduler no disponible"
            
            if not self.scheduler.is_running():
                return "ℹ️ Grid Trading ya está detenido"
            
            self.scheduler.stop()
            return "🛑 Grid Trading detenido correctamente"
            
        except Exception as e:
            return f"❌ Error deteniendo Grid Trading: {str(e)}"

    def _handle_status(self) -> str:
        """Maneja el comando status."""
        try:
            if not self.scheduler:
                return "❌ Scheduler no disponible"
            
            status = self.scheduler.get_status()
            
            message = "📊 <b>ESTADO GRID TRADING</b>\n\n"
            message += f"🔧 <b>Scheduler:</b> {status.get('status', 'unknown')}\n"
            message += f"⏰ <b>Monitoreo:</b> cada {status.get('monitoring_interval_hours', 'N/A')} hora(s)\n"
            
            if hasattr(self.scheduler, 'exchange_service'):
                trading_mode = self.scheduler.exchange_service.get_trading_mode()
                mode_emoji = "🧪" if trading_mode == "sandbox" else "🚀"
                message += f"{mode_emoji} <b>Modo:</b> {trading_mode.upper()}\n"
            
            return message
            
        except Exception as e:
            return f"❌ Error obteniendo estado: {str(e)}"

    def _handle_sandbox(self) -> str:
        """Maneja el comando sandbox."""
        try:
            if hasattr(self.scheduler, 'exchange_service'):
                self.scheduler.exchange_service.switch_to_sandbox()
                return "🧪 Cambiado a modo SANDBOX (pruebas)"
            return "❌ Exchange service no disponible"
        except Exception as e:
            return f"❌ Error cambiando a sandbox: {str(e)}"

    def _handle_production(self, command: str) -> str:
        """Maneja el comando production."""
        try:
            if not hasattr(self.scheduler, 'exchange_service'):
                return "❌ Exchange service no disponible"
            
            if "confirm" not in command:
                return (
                    "⚠️ <b>ATENCIÓN:</b> Cambio a modo PRODUCCIÓN\n\n"
                    "Esto activará trading real con dinero real.\n"
                    "Para confirmar, envía: <code>production confirm</code>"
                )
            
            self.scheduler.exchange_service.switch_to_production()
            return "🚀 Cambiado a modo PRODUCCIÓN (dinero real)"
            
        except Exception as e:
            return f"❌ Error cambiando a producción: {str(e)}"

    def _handle_manual_monitor(self) -> str:
        """Maneja el comando monitor."""
        try:
            if not self.scheduler:
                return "❌ Scheduler no disponible"
            
            result = self.scheduler.trigger_manual_monitoring()
            
            if result.get('success', False):
                return "✅ Monitoreo manual ejecutado correctamente"
            else:
                return f"❌ Error en monitoreo manual: {result.get('error', 'Error desconocido')}"
                
        except Exception as e:
            return f"❌ Error ejecutando monitoreo: {str(e)}" 