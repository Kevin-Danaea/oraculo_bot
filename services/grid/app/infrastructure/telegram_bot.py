"""
Bot de Telegram simplificado para comandos básicos del Grid Trading.
"""
from typing import Optional
import threading

from shared.services.telegram_trading import TelegramTradingService
from shared.services.logging_config import get_logger
from app.application.mode_switch_use_case import ModeSwitchUseCase

logger = get_logger(__name__)

class GridTelegramBot:
    """Bot de Telegram simplificado para control básico del Grid Trading."""
    
    def __init__(self, scheduler_instance):
        """Inicializa el bot de Telegram."""
        self.scheduler = scheduler_instance
        self.telegram_service = TelegramTradingService()
        self.is_active = False
        self.polling_thread = None
        
        # Inicializar caso de uso para cambio de modo
        if hasattr(scheduler_instance, 'grid_repository') and hasattr(scheduler_instance, 'exchange_service') and hasattr(scheduler_instance, 'notification_service'):
            self.mode_switch_use_case = ModeSwitchUseCase(
                grid_repository=scheduler_instance.grid_repository,
                exchange_service=scheduler_instance.exchange_service,
                notification_service=scheduler_instance.notification_service
            )
        else:
            self.mode_switch_use_case = None
            
        logger.info("✅ GridTelegramBot inicializado")

    def start(self):
        """Marca el bot como activo e inicia el polling para comandos interactivos."""
        try:
            self.is_active = True
            
            # Inicializar bot interactivo
            if self.telegram_service.init_bot():
                # Registrar comandos
                self._register_commands()
                
                # Iniciar polling en hilo separado
                self.polling_thread = self.telegram_service.start_polling()
                
                logger.info("✅ Bot de Telegram activado con comandos interactivos")
                return True
            else:
                logger.error("❌ No se pudo inicializar el bot interactivo")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error activando bot de Telegram: {e}")
            return False

    def stop(self):
        """Marca el bot como inactivo y detiene el polling."""
        self.is_active = False
        if self.polling_thread and self.polling_thread.is_alive():
            # El bot se detendrá automáticamente cuando el hilo termine
            logger.info("🛑 Bot de Telegram desactivado")
        return True

    def _register_commands(self):
        """Registra todos los comandos disponibles en el bot."""
        try:
            # Verificar que la aplicación esté inicializada
            if not self.telegram_service._application:
                logger.error("❌ Aplicación de Telegram no inicializada")
                return
            
            # Importar CommandHandler aquí para evitar problemas de importación
            from telegram.ext import CommandHandler
            
            # Comandos básicos - usar wrappers simples
            self.telegram_service._application.add_handler(
                CommandHandler("start", self._handle_start_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("help", self._handle_help_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("status", self._handle_status_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("balance", self._handle_balance_command)
            )
            
            # Comandos de control
            self.telegram_service._application.add_handler(
                CommandHandler("start_bot", self._handle_start_bot_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("stop_bot", self._handle_stop_bot_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("monitor", self._handle_monitor_command)
            )
            
            # Comandos de modo
            self.telegram_service._application.add_handler(
                CommandHandler("sandbox", self._handle_sandbox_command)
            )
            self.telegram_service._application.add_handler(
                CommandHandler("production", self._handle_production_command)
            )
            
            logger.info("✅ Comandos de Telegram registrados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error registrando comandos: {e}")

    def send_message(self, message: str):
        """Envía un mensaje por Telegram."""
        try:
            return self.telegram_service.send_message(message)
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            return False

    def handle_command(self, command: str) -> str:
        """Maneja comandos básicos del Grid Trading (para testing via API)."""
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
            elif command == "balance":
                return self._handle_balance_check()
            else:
                return (
                    "🤖 <b>Comandos disponibles:</b>\n\n"
                    "• <code>start_bot</code> - Iniciar Grid Trading\n"
                    "• <code>stop_bot</code> - Detener Grid Trading\n"
                    "• <code>status</code> - Ver estado del sistema\n"
                    "• <code>sandbox</code> - Cambiar a modo pruebas\n"
                    "• <code>production</code> - Cambiar a modo real\n"
                    "• <code>monitor</code> - Ejecutar monitoreo manual\n"
                    "• <code>balance</code> - Verificar capital y balances"
                )
                
        except Exception as e:
            logger.error(f"❌ Error procesando comando {command}: {e}")
            return f"❌ Error procesando comando: {str(e)}"

    # === MANEJADORES DE COMANDOS INTERACTIVOS ===
    
    async def _handle_start_command(self, update, context):
        """Maneja el comando /start."""
        message = (
            "🚀 <b>Bienvenido al Grid Trading Bot</b>\n\n"
            "Este bot te permite controlar el sistema de Grid Trading.\n\n"
            "📋 <b>Comandos principales:</b>\n"
            "• /status - Ver estado del sistema\n"
            "• /balance - Verificar capital y balances\n"
            "• /start_bot - Iniciar Grid Trading\n"
            "• /stop_bot - Detener Grid Trading\n"
            "• /monitor - Ejecutar monitoreo manual\n"
            "• /sandbox - Cambiar a modo pruebas\n"
            "• /production - Cambiar a modo real\n"
            "• /help - Ver todos los comandos\n\n"
            "¡Usa /help para ver todos los comandos disponibles!"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='HTML')

    async def _handle_help_command(self, update, context):
        """Maneja el comando /help."""
        message = (
            "🤖 <b>Comandos del Grid Trading Bot</b>\n\n"
            "📊 <b>Información:</b>\n"
            "• /status - Estado del sistema y scheduler\n"
            "• /balance - Capital asignado y balances por bot\n\n"
            "🎮 <b>Control:</b>\n"
            "• /start_bot - Iniciar Grid Trading\n"
            "• /stop_bot - Detener Grid Trading\n"
            "• /monitor - Ejecutar monitoreo manual\n\n"
            "⚙️ <b>Configuración:</b>\n"
            "• /sandbox - Cambiar a modo pruebas\n"
            "• /production - Cambiar a modo real (requiere confirmación)\n\n"
            "💡 <b>Tip:</b> Los comandos también funcionan sin la barra /"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='HTML')

    async def _handle_status_command(self, update, context):
        """Maneja el comando /status."""
        try:
            status_text = self._handle_status()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=status_text, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error obteniendo estado: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_balance_command(self, update, context):
        """Maneja el comando /balance."""
        try:
            balance_text = self._handle_balance_check()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=balance_text, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error obteniendo balances: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_start_bot_command(self, update, context):
        """Maneja el comando /start_bot."""
        try:
            result = self._handle_start_bot()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error iniciando bot: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_stop_bot_command(self, update, context):
        """Maneja el comando /stop_bot."""
        try:
            result = self._handle_stop_bot()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error deteniendo bot: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_monitor_command(self, update, context):
        """Maneja el comando /monitor."""
        try:
            result = self._handle_manual_monitor()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error ejecutando monitoreo: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_sandbox_command(self, update, context):
        """Maneja el comando /sandbox."""
        try:
            result = self._handle_sandbox()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error cambiando a sandbox: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    async def _handle_production_command(self, update, context):
        """Maneja el comando /production."""
        try:
            result = self._handle_production("production")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result, parse_mode='HTML')
        except Exception as e:
            error_msg = f"❌ Error cambiando a producción: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

    # === MANEJADORES EXISTENTES (sin cambios) ===

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
            if not self.mode_switch_use_case:
                return "❌ ModeSwitchUseCase no disponible"
            
            # Ejecutar cambio de modo con limpieza completa
            result = self.mode_switch_use_case.switch_to_sandbox()
            
            if result.get('exchange_cancelled_orders', 0) > 0 or result.get('db_cancelled_orders', 0) > 0:
                message = f"🧪 <b>Cambiado a modo SANDBOX</b>\n\n"
                message += f"🚫 Órdenes canceladas en exchange: {result.get('exchange_cancelled_orders', 0)}\n"
                message += f"🗄️ Órdenes canceladas en BD: {result.get('db_cancelled_orders', 0)}\n"
                if result.get('sold_positions'):
                    message += f"💰 Posiciones liquidadas: {list(result.get('sold_positions', {}).keys())}\n"
                return message
            else:
                return "🧪 Cambiado a modo SANDBOX (sin órdenes activas)"
                
        except Exception as e:
            return f"❌ Error cambiando a sandbox: {str(e)}"

    def _handle_production(self, command: str) -> str:
        """Maneja el comando production."""
        try:
            if not self.mode_switch_use_case:
                return "❌ ModeSwitchUseCase no disponible"
            
            if "confirm" not in command:
                return (
                    "⚠️ <b>ATENCIÓN:</b> Cambio a modo PRODUCCIÓN\n\n"
                    "Esto activará trading real con dinero real.\n"
                    "Para confirmar, envía: <code>production confirm</code>"
                )
            
            # Ejecutar cambio de modo con limpieza completa
            result = self.mode_switch_use_case.switch_to_production()
            
            if result.get('exchange_cancelled_orders', 0) > 0 or result.get('db_cancelled_orders', 0) > 0:
                message = f"🚀 <b>Cambiado a modo PRODUCCIÓN</b>\n\n"
                message += f"🚫 Órdenes canceladas en exchange: {result.get('exchange_cancelled_orders', 0)}\n"
                message += f"🗄️ Órdenes canceladas en BD: {result.get('db_cancelled_orders', 0)}\n"
                if result.get('sold_positions'):
                    message += f"💰 Posiciones liquidadas: {list(result.get('sold_positions', {}).keys())}\n"
                return message
            else:
                return "🚀 Cambiado a modo PRODUCCIÓN (sin órdenes activas)"
            
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

    def _handle_balance_check(self) -> str:
        """Maneja el comando balance."""
        try:
            if not self.scheduler:
                return "❌ Scheduler no disponible"
            
            if not hasattr(self.scheduler, 'grid_repository') or not hasattr(self.scheduler, 'exchange_service'):
                return "❌ Servicios no disponibles"
            
            # Obtener configuraciones activas
            active_configs = self.scheduler.grid_repository.get_active_configs()
            
            if not active_configs:
                return "ℹ️ No hay bots activos para verificar balances"
            
            message = "💰 <b>ESTADO DE CAPITAL Y BALANCES</b>\n\n"
            
            for config in active_configs[:3]:  # Limitar a 3 para evitar mensajes muy largos
                try:
                    pair = config.pair
                    configured_capital = config.total_capital
                    
                    # Obtener balance asignado al bot específico
                    bot_balance = self.scheduler.exchange_service.get_bot_allocated_balance(config)
                    
                    # Validar capital con aislamiento
                    validation = self.scheduler.grid_calculator.validate_capital_usage(
                        config, self.scheduler.exchange_service, 
                        self.scheduler.exchange_service.get_current_price(pair)
                    )
                    
                    message += f"📊 <b>{pair}</b>\n"
                    message += f"🎯 Capital asignado: ${configured_capital:.2f}\n"
                    message += f"🔒 Capital asignado al bot: ${bot_balance['allocated_capital']:.2f}\n"
                    message += f"💰 Capital disponible en cuenta: ${bot_balance['total_available_in_account']:.2f}\n"
                    message += f"✅ Capital utilizable por bot: ${bot_balance['total_value_usdt']:.2f}\n"
                    message += f"🪙 Balance base asignado: {bot_balance['base_balance']:.6f} {pair.split('/')[0]}\n"
                    message += f"💵 Balance USDT asignado: ${bot_balance['quote_balance']:.2f}\n"
                    
                    if bot_balance['total_available_in_account'] >= bot_balance['allocated_capital']:
                        message += f"✅ Aislamiento de capital respetado\n\n"
                    else:
                        message += f"⚠️ Capital insuficiente para aislamiento\n\n"
                        
                except Exception as e:
                    message += f"❌ Error en {config.pair}: {str(e)}\n\n"
            
            return message
                
        except Exception as e:
            return f"❌ Error obteniendo balances: {str(e)}" 