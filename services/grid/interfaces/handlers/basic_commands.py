"""
Handler para comandos básicos del Grid Bot.
Maneja comandos como start, status, delete_config, etc.
"""
import threading
import time
from datetime import datetime

from shared.services.telegram_bot_service import TelegramBot
from shared.services.logging_config import get_logger
from services.grid.schedulers.grid_scheduler import (
    get_grid_scheduler,
    start_grid_bot_scheduler, 
    stop_grid_bot_scheduler,
    start_grid_bot_manual,
    stop_grid_bot_manual,
    get_grid_bot_status
)
from .base_handler import BaseHandler

logger = get_logger(__name__)


class BasicCommandsHandler(BaseHandler):
    """Handler para comandos básicos del Grid Bot"""
    
    def handle_start_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start"""
        try:
            # Limpiar estados de conversación
            bot.clear_conversation_state(chat_id)
            
            message = """
🤖 GRID BOT V3.0 - MODO AUTÓNOMO

🧠 Nueva Arquitectura Inteligente:
• El Grid responde automáticamente a las decisiones del Cerebro
• Monitoreo continuo cada 10 minutos
• Activación/desactivación automática según condiciones del mercado

📱 Comandos Disponibles:

Configuración:
• /config - Configurar parámetros del bot
• /info_config - Ver configuración actual
• /delete_config - Eliminar configuración

Control Manual:
• /start_bot - Iniciar trading manualmente (consulta al cerebro)
• /stop_bot - Detener trading manualmente
• /restart_bot - Reiniciar bot
• /status - Estado actual del sistema

Modo de Trading:
• /modo_productivo - Cambiar a trading real
• /modo_sandbox - Cambiar a paper trading
• /modo_actual - Ver modo actual

Información del Cerebro:
• /estado_cerebro - Ver análisis detallado del cerebro

🔄 Funcionamiento Autónomo:
• El Cerebro analiza el mercado cada 2 horas
• Si autoriza trading → Grid se activa automáticamente
• Si recomienda pausar → Grid se detiene automáticamente
• Notificaciones automáticas por Telegram

💡 Uso Recomendado:
1. Configura con /config
2. El sistema funciona automáticamente
3. Usa /status para monitorear
4. Interviene solo si necesitas cambiar estrategia
"""
            
            # Verificar estado actual y modo
            from services.grid.core.cerebro_integration import obtener_configuracion_trading
            trading_config = obtener_configuracion_trading()
            modo_icon = "🟡" if trading_config['modo'] == 'SANDBOX' else "🟢"
            
            scheduler = get_grid_scheduler()
            if scheduler and scheduler.running:
                message += "🟢 Estado Bot: Ejecutándose\n"
            else:
                message += "🔴 Estado Bot: Detenido\n"
            
            message += f"{modo_icon} Modo Trading: {trading_config['modo']}\n"
            
            # Verificar si tiene configuración guardada
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"⚙️ Configuración: {user_config.pair} con ${user_config.total_capital}\n"
            else:
                message += "⚙️ Configuración: No configurado\n"
            
            message += "\n📋 Comandos principales:\n"
            message += "/config - Configurar bot (solo par + capital)\n"
            message += "/start_bot - Iniciar trading inteligente\n"
            message += "/stop_bot - Detener bot\n"
            message += "/status - Estado completo (bot + cerebro)\n"
            message += "/balance - Ver balance actual y P&L\n\n"
            message += "🔄 Control de modo trading:\n"
            message += "/modo_productivo - Cambiar a dinero real ⚠️\n"
            message += "/modo_sandbox - Cambiar a simulación ✅\n"
            message += "/modo_actual - Ver modo activo\n\n"
            message += "🧠 Estado del cerebro:\n"
            message += "/estado_cerebro - Ver análisis del cerebro\n\n"
            message += "🛡️ Protecciones:\n"
            message += "/protections - Ver estado stop-loss\n"
            message += "/set_stop_loss X - Configurar % stop-loss\n\n"
            message += "📊 Información:\n"
            message += "/info_config - Info sobre configuración optimizada\n"
            message += "/configs - Ver todas las configuraciones (ETH, BTC, MATIC)\n\n"
            message += "🔄 Gestión Multibot:\n"
            message += "/activate_eth - Cambiar a configuración ETH\n"
            message += "/activate_btc - Cambiar a configuración BTC\n"
            message += "/activate_matic - Cambiar a configuración MATIC\n"
            message += "/update_capital X - Cambiar capital de configuración activa\n"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "comando start", e)
    
    def handle_start_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start_bot - V2 con modo manual"""
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if MODO_PRODUCTIVO:
                # MODO PRODUCTIVO: Requiere configuración guardada
                user_config = self.get_user_config(chat_id)
                if not user_config:
                    message = "⚠️ No tienes configuración guardada\n\n"
                    message += "Usa /config para configurar el bot primero."
                    bot.send_message(chat_id, message)
                    return
            else:
                # MODO SANDBOX: Usar configuración fija
                user_config = None  # No necesitamos config de BD en sandbox
            
            # Verificar estado del bot
            bot_status = get_grid_bot_status()
            if bot_status['bot_running']:
                bot.send_message(chat_id, "⚠️ El bot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            if not bot_status['ready_to_start']:
                message = "⚠️ Servicio no está listo\n\n"
                message += "El scheduler no está activo. Contacta al administrador."
                bot.send_message(chat_id, message)
                return
            
            # Iniciar bot manualmente
            def start_bot_async():
                try:
                    # PRIMERO: Consultar estado del cerebro
                    bot.send_message(chat_id, "🧠 Consultando estado del Cerebro...")
                    
                    try:
                        from services.grid.core.cerebro_integration import consultar_estado_inicial_cerebro
                        import asyncio
                        
                        # Crear event loop para la consulta asíncrona
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            # Consultar al cerebro
                            resultado_cerebro = loop.run_until_complete(consultar_estado_inicial_cerebro())
                            
                            # Verificar que resultado_cerebro sea un diccionario
                            if isinstance(resultado_cerebro, dict):
                                # Analizar respuesta del cerebro
                                if resultado_cerebro.get('puede_operar', False):
                                    decision_cerebro = "🟢 OPERAR_GRID"
                                    mensaje_cerebro = "✅ El Cerebro autoriza el trading"
                                else:
                                    decision_cerebro = "🔴 PAUSAR_GRID"
                                    mensaje_cerebro = "⚠️ El Cerebro recomienda pausar el trading"
                                
                                # Mostrar resultado del cerebro
                                bot.send_message(
                                    chat_id, 
                                    f"🧠 Estado del Cerebro:\n"
                                    f"• Decisión: {decision_cerebro}\n"
                                    f"• Razón: {resultado_cerebro.get('razon', 'No disponible')}\n"
                                    f"• {mensaje_cerebro}"
                                )
                                
                                # Si el cerebro dice PAUSAR, preguntar si continuar
                                if not resultado_cerebro.get('puede_operar', False):
                                    bot.send_message(
                                        chat_id,
                                        "⚠️ El Cerebro recomienda pausar el trading\n\n"
                                        "¿Deseas continuar de todas formas?\n"
                                        "Responde 'SI' para continuar o 'NO' para cancelar."
                                    )
                                    # Aquí podrías implementar un sistema de confirmación
                                    # Por ahora, continuamos con advertencia
                                    bot.send_message(chat_id, "⚠️ Continuando con advertencia...")
                            else:
                                bot.send_message(
                                    chat_id,
                                    f"⚠️ Respuesta inesperada del Cerebro: {resultado_cerebro}\n"
                                    f"Continuando en modo standalone..."
                                )
                            
                        finally:
                            loop.close()
                            
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"⚠️ No se pudo consultar al Cerebro: {str(e)}\n"
                            f"Continuando en modo standalone..."
                        )
                    
                    # SEGUNDO: Iniciar el grid bot
                    bot.send_message(chat_id, "🚀 Iniciando Grid Bot...")
                    success, result_message = start_grid_bot_manual()
                    
                    if success:
                        if MODO_PRODUCTIVO and user_config:
                            message = f"🚀 ¡Grid Bot iniciado exitosamente!\n\n"
                            message += f"📊 Trading: {user_config.pair}\n"
                            message += f"💰 Capital: ${user_config.total_capital} USDT\n"
                            message += f"🎚️ Niveles: {user_config.grid_levels}\n"
                            message += f"📊 Rango: ±{user_config.price_range_percent}%\n\n"
                            message += f"🛡️ Protecciones V2:\n"
                            message += f"• Stop-Loss: {'✅' if getattr(user_config, 'enable_stop_loss', True) else '❌'} ({getattr(user_config, 'stop_loss_percent', 5.0)}%)\n"
                            message += f"• Trailing Up: {'✅' if getattr(user_config, 'enable_trailing_up', True) else '❌'}\n\n"
                            message += f"📈 Usa /status para monitorear el progreso."
                        else:
                            message = f"🚀 ¡Grid Bot iniciado exitosamente!\n\n"
                            message += f"🟡 MODO SANDBOX (Paper Trading)\n\n"
                            message += f"📊 Trading: ETH/USDT\n"
                            message += f"💰 Capital: $1,000.00 USDT (fijo)\n"
                            message += f"🎚️ Niveles: 30 (óptimo validado)\n"
                            message += f"📊 Rango: ±10% (óptimo validado)\n\n"
                            message += f"🛡️ Protecciones V2:\n"
                            message += f"• Stop-Loss: ✅ (5.0%)\n"
                            message += f"• Trailing Up: ✅ (Optimiza ganancias)\n\n"
                            message += f"📈 Usa /status para monitorear el progreso."
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ Error iniciando bot: {result_message}")
                        
                except Exception as e:
                    self.send_error_message(bot, chat_id, "start_bot_async", e)
            
            threading.Thread(target=start_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "start_bot", e)
    
    def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /stop_bot - V2 con modo manual"""
        try:
            # Verificar estado del bot
            bot_status = get_grid_bot_status()
            if not bot_status['bot_running']:
                bot.send_message(chat_id, "ℹ️ El bot ya está detenido (modo standby).")
                return
            
            if not bot_status['ready_to_stop']:
                message = "⚠️ <b>No se puede detener el bot</b>\n\n"
                message += "El bot no está en un estado válido para detener."
                bot.send_message(chat_id, message)
                return
            
            def stop_bot_async():
                try:
                    success, result_message = stop_grid_bot_manual()
                    
                    if success:
                        message = "🛑 <b>Grid Bot detenido correctamente</b>\n\n"
                        message += "✅ Se señaló la parada del bot\n"
                        message += "🧹 Las órdenes serán canceladas automáticamente\n"
                        message += "⏸️ Bot entrando en modo standby\n\n"
                        message += "ℹ️ <i>El proceso de cancelación puede tomar unos segundos</i>\n"
                        message += "▶️ Usa /start_bot para reanudar trading"
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ <b>Error deteniendo bot:</b> {result_message}")
                        
                except Exception as e:
                    self.send_error_message(bot, chat_id, "stop_bot_async", e)
            
            threading.Thread(target=stop_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Deteniendo Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "stop_bot", e)
    
    def handle_restart_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /restart_bot"""
        try:
            def restart_bot_async():
                try:
                    # Detener si está ejecutándose
                    scheduler = get_grid_scheduler()
                    if scheduler and scheduler.running:
                        bot.send_message(chat_id, "🛑 Deteniendo bot actual...")
                        stop_grid_bot_scheduler()
                        time.sleep(3)  # Esperar un poco
                    
                    # Iniciar de nuevo
                    bot.send_message(chat_id, "🚀 Reiniciando bot...")
                    start_grid_bot_scheduler()
                    
                    user_config = self.get_user_config(chat_id)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>Bot reiniciado correctamente</b>\n\n"
                        f"📊 Trading: {user_config.pair if user_config else 'N/A'}\n"
                        f"Usa /status para verificar el estado."
                    )
                    
                except Exception as e:
                    self.send_error_message(bot, chat_id, "reiniciando bot", e)
            
            threading.Thread(target=restart_bot_async, daemon=True).start()
            bot.send_message(chat_id, "🔄 Reiniciando Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "restart_bot", e)
    
    def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """
        Comando /status: Muestra estado del grid bot con integración Cerebro
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO, estado_cerebro, obtener_configuracion_trading
            
            # Obtener estado del scheduler
            scheduler = get_grid_scheduler()
            is_running = scheduler.running if scheduler else False
            
            # Obtener estado del cerebro y modo de trading
            try:
                cerebro_estado = estado_cerebro
                config_trading = obtener_configuracion_trading()
            except ImportError:
                cerebro_estado = {"decision": "No disponible", "fuente": "error"}
                config_trading = {"modo": "No disponible"}
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if MODO_PRODUCTIVO:
                # MODO PRODUCTIVO: Requiere configuración guardada
                user_config = self.get_user_config(chat_id)
                
                if user_config:
                    status_message = f"""
🤖 ESTADO DEL GRID BOT

📊 Configuración Activa:
• Par: {user_config.pair}
• Capital: ${user_config.total_capital:,.2f}
• Niveles: {user_config.grid_levels}
• Rango: {user_config.price_range_percent}%

🔄 Estado del Sistema:
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• Modo Operación: 🧠 AUTÓNOMO (Responde a decisiones del Cerebro)

🧠 Estado del Cerebro:
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}

⚡ Protecciones Avanzadas:
• Stop Loss: {'🟢 Activo' if getattr(user_config, 'enable_stop_loss', False) else '🔴 Inactivo'}
• Trailing Up: {'🟢 Activo' if getattr(user_config, 'enable_trailing_up', False) else '🔴 Inactivo'}
"""
                    
                    if hasattr(user_config, 'enable_stop_loss') and getattr(user_config, 'enable_stop_loss', False):
                        status_message += f"• Stop Loss %: {getattr(user_config, 'stop_loss_percent', 5.0)}%\n"
                else:
                    status_message = f"""
🤖 ESTADO DEL GRID BOT

⚠️ Sin configuración activa
Usa /config para configurar el bot

🔄 Estado del Sistema:
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• Modo Operación: 🧠 AUTÓNOMO (Responde a decisiones del Cerebro)

🧠 Estado del Cerebro:
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}
"""
            else:
                # MODO SANDBOX: Usar configuración fija
                status_message = f"""
🤖 ESTADO DEL GRID BOT

🟡 MODO SANDBOX (Paper Trading)

📊 Configuración Fija:
• Par: ETH/USDT
• Capital: $1,000.00 USDT (fijo)
• Niveles: 30 (óptimo validado)
• Rango: 10% (óptimo validado)

🔄 Estado del Sistema:
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• Modo Operación: 🧠 AUTÓNOMO (Responde a decisiones del Cerebro)

🧠 Estado del Cerebro:
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}

⚡ Protecciones Avanzadas:
• Stop Loss: 🟢 Activo (5.0%)
• Trailing Up: 🟢 Activo (Optimiza ganancias)
"""
            
            # Agregar comandos disponibles
            status_message += """

📝 Comandos Nuevos:
• /modo_productivo - Cambiar a trading real
• /modo_sandbox - Cambiar a paper trading
• /estado_cerebro - Ver estado detallado del cerebro
• /modo_actual - Ver modo de trading actual
"""
            
            bot.send_message(chat_id, status_message)
            logger.info(f"✅ Estado enviado a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener el estado: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_status_command: {e}")

    def handle_delete_config_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /delete_config"""
        try:
            user_config = self.get_user_config(chat_id)
            
            if not user_config:
                bot.send_message(chat_id, "ℹ️ No tienes configuración guardada.")
                return
            
            # Desactivar configuración en la base de datos
            if self.update_user_config(chat_id, {'is_active': False}):
                bot.send_message(
                    chat_id, 
                    f"✅ Configuración eliminada correctamente.\n\n"
                    f"Se eliminó: {user_config.pair} con ${user_config.total_capital} USDT"
                )
            else:
                bot.send_message(chat_id, "❌ Error eliminando configuración")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "eliminando config", e)

    def handle_modo_productivo_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_productivo: Cambia a modo productivo (trading real)
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO, alternar_modo_trading, obtener_configuracion_trading
            from services.grid.schedulers.grid_scheduler import get_grid_bot_status, stop_grid_bot_manual, start_grid_bot_manual

            bot_status = get_grid_bot_status()
            if MODO_PRODUCTIVO:
                config = obtener_configuracion_trading()
                message = f"""
🟢 YA EN MODO PRODUCTIVO

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

⚠️ ADVERTENCIA: Trading con dinero real
"""
                bot.send_message(chat_id, message)
                return

            # Si el bot está corriendo, detenerlo y cancelar órdenes
            if bot_status['bot_running']:
                bot.send_message(chat_id, "🛑 Deteniendo Grid Bot y cancelando órdenes por cambio de modo...")
                success, msg = stop_grid_bot_manual()
                if success:
                    bot.send_message(chat_id, "✅ Grid Bot detenido y órdenes canceladas correctamente.")
                else:
                    bot.send_message(chat_id, f"⚠️ Hubo un problema al detener el bot: {msg}")

            # Cambiar a modo productivo
            config = alternar_modo_trading()
            message = f"""
🟢 CAMBIADO A MODO PRODUCTIVO

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

⚠️ ADVERTENCIA IMPORTANTE:
Ahora estás operando con DINERO REAL en Binance.
Todas las operaciones afectarán tu cuenta real.

🔄 Usa /modo_sandbox para volver a paper trading
"""
            bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_productivo ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            bot.send_message(chat_id, "🚀 Reiniciando Grid Bot en modo PRODUCTIVO...")
            
            # Iniciar bot con consulta al cerebro
            def start_bot_with_cerebro():
                try:
                    # PRIMERO: Consultar estado del cerebro
                    bot.send_message(chat_id, "🧠 Consultando estado del Cerebro...")
                    
                    try:
                        from services.grid.core.cerebro_integration import consultar_estado_inicial_cerebro
                        import asyncio
                        
                        # Crear event loop para la consulta asíncrona
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            # Consultar al cerebro
                            resultado_cerebro = loop.run_until_complete(consultar_estado_inicial_cerebro())
                            
                            # Verificar que resultado_cerebro sea un diccionario
                            if isinstance(resultado_cerebro, dict):
                                # Analizar respuesta del cerebro
                                if resultado_cerebro.get('puede_operar', False):
                                    decision_cerebro = "🟢 OPERAR_GRID"
                                    mensaje_cerebro = "✅ El Cerebro autoriza el trading"
                                else:
                                    decision_cerebro = "🔴 PAUSAR_GRID"
                                    mensaje_cerebro = "⚠️ El Cerebro recomienda pausar el trading"
                                
                                # Mostrar resultado del cerebro
                                bot.send_message(
                                    chat_id, 
                                    f"🧠 Estado del Cerebro:\n"
                                    f"• Decisión: {decision_cerebro}\n"
                                    f"• Razón: {resultado_cerebro.get('razon', 'No disponible')}\n"
                                    f"• {mensaje_cerebro}"
                                )
                                
                                # Si el cerebro dice PAUSAR, preguntar si continuar
                                if not resultado_cerebro.get('puede_operar', False):
                                    bot.send_message(
                                        chat_id,
                                        "⚠️ El Cerebro recomienda pausar el trading\n\n"
                                        "¿Deseas continuar de todas formas?\n"
                                        "Responde 'SI' para continuar o 'NO' para cancelar."
                                    )
                                    # Aquí podrías implementar un sistema de confirmación
                                    # Por ahora, continuamos con advertencia
                                    bot.send_message(chat_id, "⚠️ Continuando con advertencia...")
                            else:
                                bot.send_message(
                                    chat_id,
                                    f"⚠️ Respuesta inesperada del Cerebro: {resultado_cerebro}\n"
                                    f"Continuando en modo standalone..."
                                )
                            
                        finally:
                            loop.close()
                            
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"⚠️ No se pudo consultar al Cerebro: {str(e)}\n"
                            f"Continuando en modo standalone..."
                        )
                    
                    # SEGUNDO: Iniciar el grid bot
                    bot.send_message(chat_id, "🚀 Iniciando Grid Bot...")
                    success, result_message = start_grid_bot_manual()
                    
                    if success:
                        # Obtener configuración del usuario para mostrar detalles
                        user_config = self.get_user_config(chat_id)
                        if user_config:
                            message = f"🚀 ¡Grid Bot iniciado exitosamente en modo PRODUCTIVO!\n\n"
                            message += f"📊 Trading: {user_config.pair}\n"
                            message += f"💰 Capital: ${user_config.total_capital} USDT\n"
                            message += f"🎚️ Niveles: {user_config.grid_levels}\n"
                            message += f"📊 Rango: ±{user_config.price_range_percent}%\n\n"
                            message += f"🛡️ Protecciones:\n"
                            message += f"• Stop-Loss: {'✅' if getattr(user_config, 'enable_stop_loss', True) else '❌'} ({getattr(user_config, 'stop_loss_percent', 5.0)}%)\n"
                            message += f"• Trailing Up: {'✅' if getattr(user_config, 'enable_trailing_up', True) else '❌'}\n\n"
                            message += f"📈 Usa /status para monitorear el progreso."
                        else:
                            message = f"🚀 ¡Grid Bot iniciado exitosamente en modo PRODUCTIVO!\n\n"
                            message += f"⚠️ No hay configuración personalizada\n"
                            message += f"Usa /config para configurar el bot\n\n"
                            message += f"📈 Usa /status para monitorear el progreso."
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ Error iniciando bot: {result_message}")
                        
                except Exception as e:
                    bot.send_message(chat_id, f"❌ Error iniciando bot: {str(e)}")
            
            threading.Thread(target=start_bot_with_cerebro, daemon=True).start()

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo productivo: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_productivo_command: {e}")

    def handle_modo_sandbox_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_sandbox: Cambia a modo sandbox (paper trading)
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO, alternar_modo_trading, obtener_configuracion_trading
            from services.grid.schedulers.grid_scheduler import get_grid_bot_status, stop_grid_bot_manual, start_grid_bot_manual

            bot_status = get_grid_bot_status()
            if not MODO_PRODUCTIVO:
                config = obtener_configuracion_trading()
                message = f"""
🟡 YA EN MODO SANDBOX

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

✅ SEGURO: Paper trading sin riesgo
"""
                bot.send_message(chat_id, message)
                return

            # Si el bot está corriendo, detenerlo y cancelar órdenes
            if bot_status['bot_running']:
                bot.send_message(chat_id, "🛑 Deteniendo Grid Bot y cancelando órdenes por cambio de modo...")
                success, msg = stop_grid_bot_manual()
                if success:
                    bot.send_message(chat_id, "✅ Grid Bot detenido y órdenes canceladas correctamente.")
                else:
                    bot.send_message(chat_id, f"⚠️ Hubo un problema al detener el bot: {msg}")

            # Cambiar a modo sandbox
            config = alternar_modo_trading()
            message = f"""
🟡 CAMBIADO A MODO SANDBOX

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

✅ MODO SEGURO ACTIVADO:
Todas las operaciones son simuladas.
No se usa dinero real.

🔄 Usa /modo_productivo para trading real
"""
            bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_sandbox ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            bot.send_message(chat_id, "🚀 Reiniciando Grid Bot en modo SANDBOX...")
            
            # Iniciar bot con consulta al cerebro
            def start_bot_with_cerebro():
                try:
                    # PRIMERO: Consultar estado del cerebro
                    bot.send_message(chat_id, "🧠 Consultando estado del Cerebro...")
                    
                    try:
                        from services.grid.core.cerebro_integration import consultar_estado_inicial_cerebro
                        import asyncio
                        
                        # Crear event loop para la consulta asíncrona
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            # Consultar al cerebro
                            resultado_cerebro = loop.run_until_complete(consultar_estado_inicial_cerebro())
                            
                            # Verificar que resultado_cerebro sea un diccionario
                            if isinstance(resultado_cerebro, dict):
                                # Analizar respuesta del cerebro
                                if resultado_cerebro.get('puede_operar', False):
                                    decision_cerebro = "🟢 OPERAR_GRID"
                                    mensaje_cerebro = "✅ El Cerebro autoriza el trading"
                                else:
                                    decision_cerebro = "🔴 PAUSAR_GRID"
                                    mensaje_cerebro = "⚠️ El Cerebro recomienda pausar el trading"
                                
                                # Mostrar resultado del cerebro
                                bot.send_message(
                                    chat_id, 
                                    f"🧠 Estado del Cerebro:\n"
                                    f"• Decisión: {decision_cerebro}\n"
                                    f"• Razón: {resultado_cerebro.get('razon', 'No disponible')}\n"
                                    f"• {mensaje_cerebro}"
                                )
                                
                                # Si el cerebro dice PAUSAR, preguntar si continuar
                                if not resultado_cerebro.get('puede_operar', False):
                                    bot.send_message(
                                        chat_id,
                                        "⚠️ El Cerebro recomienda pausar el trading\n\n"
                                        "¿Deseas continuar de todas formas?\n"
                                        "Responde 'SI' para continuar o 'NO' para cancelar."
                                    )
                                    # Aquí podrías implementar un sistema de confirmación
                                    # Por ahora, continuamos con advertencia
                                    bot.send_message(chat_id, "⚠️ Continuando con advertencia...")
                            else:
                                bot.send_message(
                                    chat_id,
                                    f"⚠️ Respuesta inesperada del Cerebro: {resultado_cerebro}\n"
                                    f"Continuando en modo standalone..."
                                )
                            
                        finally:
                            loop.close()
                            
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"⚠️ No se pudo consultar al Cerebro: {str(e)}\n"
                            f"Continuando en modo standalone..."
                        )
                    
                    # SEGUNDO: Iniciar el grid bot
                    bot.send_message(chat_id, "🚀 Iniciando Grid Bot...")
                    success, result_message = start_grid_bot_manual()
                    
                    if success:
                        message = f"🚀 ¡Grid Bot iniciado exitosamente en modo SANDBOX!\n\n"
                        message += f"📊 Trading: ETH/USDT (sandbox)\n"
                        message += f"💰 Capital: $1000 USDT (simulado)\n"
                        message += f"🎚️ Niveles: 30 (fijo)\n"
                        message += f"📊 Rango: ±10% (fijo)\n\n"
                        message += f"🛡️ Protecciones:\n"
                        message += f"• Stop-Loss: ✅ (5%)\n"
                        message += f"• Trailing Up: ✅ Activo (Optimiza ganancias)\n\n"
                        message += f"📈 Usa /status para monitorear el progreso."
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ Error iniciando bot: {result_message}")
                        
                except Exception as e:
                    bot.send_message(chat_id, f"❌ Error iniciando bot: {str(e)}")
            
            threading.Thread(target=start_bot_with_cerebro, daemon=True).start()

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo sandbox: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_sandbox_command: {e}")

    def handle_estado_cerebro_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /estado_cerebro: Muestra estado detallado del cerebro
        """
        try:
            from services.grid.core.cerebro_integration import estado_cerebro
            
            message = f"""
🧠 ESTADO DETALLADO DEL CEREBRO

📊 Decisión Actual:
• Acción: {estado_cerebro.get('decision', 'No disponible')}
• Fuente: {estado_cerebro.get('fuente', 'No disponible')}
• Última actualización: {estado_cerebro.get('ultima_actualizacion', 'No disponible')}

🔄 Significado de las decisiones:
• OPERAR_GRID: Condiciones favorables para trading
• PAUSAR_GRID: Condiciones desfavorables, pausa recomendada

📡 Integración:
• Cerebro monitorea mercado cada 2 horas
• Notifica automáticamente al Grid
• Análisis basado en ADX y volatilidad
"""
            
            bot.send_message(chat_id, message)
            logger.info(f"✅ Estado del cerebro enviado a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener estado del cerebro: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_estado_cerebro_command: {e}")

    def handle_modo_actual_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_actual: Muestra el modo de trading actual
        """
        try:
            from services.grid.core.cerebro_integration import obtener_configuracion_trading
            
            config = obtener_configuracion_trading()
            modo_icon = "🟢" if config['modo'] == "PRODUCTIVO" else "🟡"
            
            message = f"""
{modo_icon} MODO DE TRADING ACTUAL

• Modo: {config['modo']}
• Descripción: {config['descripcion']}

💡 Comandos disponibles:
• /modo_productivo - Cambiar a trading real
• /modo_sandbox - Cambiar a paper trading
• /status - Estado completo del sistema
• /info_config - Info sobre configuración optimizada
"""
            
            bot.send_message(chat_id, message)
            logger.info(f"✅ Modo actual enviado a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener modo actual: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_actual_command: {e}")

    def handle_info_config_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /info_config: Muestra información sobre la configuración optimizada
        """
        try:
            from services.grid.core.cerebro_integration import obtener_configuracion_trading
            
            config = obtener_configuracion_trading()
            modo_icon = "🟢" if config['modo'] == "PRODUCTIVO" else "🟡"
            
            # Calcular capital mínimo para 30 niveles
            capital_minimo = 30 * 10  # 300 USDT (fórmula simplificada)
            
            message = f"""
📊 CONFIGURACIÓN OPTIMIZADA v3.0

🎯 Parámetros actuales (FIJOS):
• Niveles de grid: 30 (óptimo validado)
• Rango de precios: 10% (óptimo validado)
• Capital sandbox: $1000 USDT (fijo)
• Capital productivo mínimo: ${capital_minimo} USDT

🧠 Integración con Cerebro:
• ADX < 30: Condiciones favorables
• Volatilidad > 4%: Mercado activo
• Stop-loss automático: 5% por defecto
• Trailing Up: 🟢 Activo (Optimiza ganancias)

{modo_icon} Modo actual: {config['modo']}

💰 ¿Por qué ${capital_minimo} USD
• 30 niveles requieren $10 USDT por orden
• Fórmula simplificada: Niveles × $10
• Cobertura de comisiones y operaciones
• Liquidez para recompras automáticas
• Optimizado para eficiencia operativa

🔄 Evolución del sistema:

📈 VERSIÓN ACTUAL (v3.0):
• Parámetros fijos: 30 niveles, 10% rango
• Cerebro decide: ¿Cuándo operar?
• Configuración: Solo par + capital

🚀 VERSIÓN FUTURA (v4.0):
• Cerebro decide: ¿Cuándo operar?
• Cerebro decide: ¿Cuántos niveles? (dinámico)
• Cerebro decide: ¿Qué rango usar? (dinámico)
• Configuración: Solo par + capital mínimo

🧠 Cerebro Inteligente Futuro:
• Análisis de mercado en tiempo real
• Selección dinámica de parámetros
• Adaptación automática a condiciones
• Optimización continua por IA

💡 Usa /config para aplicar la configuración actual
"""
            
            bot.send_message(chat_id, message)
            logger.info(f"✅ Info configuración enviada a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener info configuración: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_info_config_command: {e}")

    def handle_balance_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /balance: Muestra el balance actual de la cuenta
        MEJORADO: Usa nueva función de P&L con explicación detallada
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if MODO_PRODUCTIVO:
                # MODO PRODUCTIVO: Requiere configuración guardada
                user_config = self.get_user_config(chat_id)
                if not user_config:
                    bot.send_message(chat_id, "⚠️ No tienes configuración guardada\n\nUsa /config para configurar el bot primero.")
                    return
                
                # Verificar que el bot esté ejecutándose para obtener balance real
                from services.grid.schedulers.grid_scheduler import get_grid_bot_status
                bot_status = get_grid_bot_status()
                
                if not bot_status['bot_running']:
                    bot.send_message(chat_id, "⚠️ El bot no está ejecutándose\n\nUsa /start_bot para iniciar el trading y poder ver el balance actual.")
                    return
                
                pair = str(user_config.pair)
                initial_capital = float(getattr(user_config, 'total_capital', 0))
                
            else:
                # MODO SANDBOX: Usar configuración fija
                pair = 'ETH/USDT'
                initial_capital = 1000.0  # Capital fijo para sandbox
                
                # En sandbox, no necesitamos verificar si el bot está corriendo
                # porque siempre podemos consultar el balance de paper trading
            
            def get_balance_async():
                try:
                    # Obtener conexión al exchange
                    from services.grid.core.config_manager import get_exchange_connection
                    exchange = get_exchange_connection()
                    
                    # Obtener balance actual
                    from shared.services.telegram_service import get_current_balance, calculate_pnl_with_explanation
                    balance = get_current_balance(exchange, pair)
                    
                    # Calcular P&L usando nueva función mejorada
                    mode = "PRODUCTIVO" if MODO_PRODUCTIVO else "SANDBOX"
                    pnl_data = calculate_pnl_with_explanation(balance, initial_capital, mode)
                    
                    # Crear mensaje con información del modo
                    modo_info = "🟢 PRODUCTIVO" if MODO_PRODUCTIVO else "🟡 SANDBOX (Paper Trading)"
                    
                    message = f"""
💰 <b>BALANCE ACTUAL</b>

{modo_info}

📊 <b>Par:</b> {pair}
💵 <b>Capital inicial:</b> ${initial_capital:,.2f}

💵 <b>USDT disponible:</b> ${balance['usdt']:.2f}
🪙 <b>{balance['crypto_symbol']} disponible:</b> {balance['crypto']:.6f}
💎 <b>Valor {balance['crypto_symbol']}:</b> ${balance['crypto_value']:.2f}
📊 <b>Total actual:</b> ${balance['total_value']:.2f}

{pnl_data['pnl_icon']} <b>P&L Total:</b> ${pnl_data['total_pnl']:.2f} ({pnl_data['total_pnl_percentage']:.2f}%)
💡 <i>Capital inicial: ${initial_capital:.2f} | {mode}</i>

💹 <b>Precio actual:</b> ${balance['current_price']:.2f}

⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>
"""
                    
                    bot.send_message(chat_id, message)
                    logger.info(f"✅ Balance enviado a chat {chat_id} (modo: {mode})")
                    
                except Exception as e:
                    error_message = f"❌ Error obteniendo balance: {str(e)}"
                    bot.send_message(chat_id, error_message)
                    logger.error(f"❌ Error en get_balance_async: {e}")
            
            # Ejecutar en hilo separado para no bloquear
            import threading
            threading.Thread(target=get_balance_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Obteniendo balance actual...")
            
        except Exception as e:
            error_message = f"❌ Error al obtener balance: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_balance_command: {e}")

    def handle_configs_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /configs: Muestra todas las configuraciones del usuario
        """
        try:
            # Obtener todas las configuraciones del usuario
            all_configs = self.get_all_user_configs(chat_id)
            
            if not all_configs:
                message = "📊 <b>CONFIGURACIONES MULTIBOT</b>\n\n"
                message += "⚠️ No tienes configuraciones guardadas\n\n"
                message += "💡 Usa /config para crear tu primera configuración"
                bot.send_message(chat_id, message)
                return
            
            message = "📊 <b>CONFIGURACIONES MULTIBOT</b>\n\n"
            
            # Agrupar configuraciones por tipo
            configs_by_type = {}
            for config in all_configs:
                config_type = getattr(config, 'config_type', 'ETH')
                if config_type not in configs_by_type:
                    configs_by_type[config_type] = []
                configs_by_type[config_type].append(config)
            
            # Mostrar cada tipo de configuración
            for config_type in ['ETH', 'BTC', 'MATIC']:
                configs = configs_by_type.get(config_type, [])
                
                if configs:
                    config = configs[0]  # Tomar la primera (debería ser la única)
                    is_active = getattr(config, 'is_active', False)
                    is_configured = getattr(config, 'is_configured', False)
                    
                    status_icon = "🟢" if is_active else "⚪"
                    config_status = "ACTIVA" if is_active else "INACTIVA"
                    configured_status = "✅ Configurada" if is_configured else "⚪ Sin configurar"
                    
                    message += f"{status_icon} <b>{config_type}</b> - {config_status}\n"
                    message += f"   📊 Par: {config.pair}\n"
                    message += f"   💰 Capital: ${config.total_capital} USDT\n"
                    message += f"   🎯 Niveles: {config.grid_levels}\n"
                    message += f"   📈 Rango: ±{config.price_range_percent}%\n"
                    message += f"   🛡️ Stop-Loss: {getattr(config, 'stop_loss_percent', 5.0)}%\n"
                    message += f"   📈 Trailing: {'✅' if getattr(config, 'enable_trailing_up', True) else '❌'}\n"
                    message += f"   📋 Estado: {configured_status}\n\n"
                else:
                    message += f"⚪ <b>{config_type}</b> - SIN CONFIGURAR\n"
                    message += f"   💡 Usa /config para configurar\n\n"
            
            message += "🔧 <b>Comandos disponibles:</b>\n"
            message += "/config - Configurar nueva configuración\n"
            message += "/activate_eth - Activar configuración ETH\n"
            message += "/activate_btc - Activar configuración BTC\n"
            message += "/activate_matic - Activar configuración MATIC\n"
            message += "/update_capital X - Actualizar capital de configuración activa\n"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "mostrando configuraciones", e)
    
    def handle_activate_eth_command(self, chat_id: str, message_text: str, bot):
        """Comando /activate_eth: Activa la configuración ETH"""
        self._handle_activate_config(chat_id, 'ETH', bot)
    
    def handle_activate_btc_command(self, chat_id: str, message_text: str, bot):
        """Comando /activate_btc: Activa la configuración BTC"""
        self._handle_activate_config(chat_id, 'BTC', bot)
    
    def handle_activate_matic_command(self, chat_id: str, message_text: str, bot):
        """Comando /activate_matic: Activa la configuración MATIC"""
        self._handle_activate_config(chat_id, 'MATIC', bot)
    
    def _handle_activate_config(self, chat_id: str, config_type: str, bot):
        """Método interno para activar una configuración específica"""
        try:
            # Verificar que la configuración existe y está configurada
            config = self.get_user_config_by_type(chat_id, config_type)
            
            if not config:
                message = f"⚠️ No tienes configuración {config_type} guardada\n\n"
                message += f"💡 Usa /config para crear la configuración {config_type} primero"
                bot.send_message(chat_id, message)
                return
            
            if not getattr(config, 'is_configured', False):
                message = f"⚠️ La configuración {config_type} no está configurada\n\n"
                message += f"💡 Usa /config para configurar {config_type} primero"
                bot.send_message(chat_id, message)
                return
            
            # Activar la configuración
            if self.activate_config(chat_id, config_type):
                message = f"✅ <b>Configuración {config_type} activada</b>\n\n"
                message += f"📊 <b>Par:</b> {config.pair}\n"
                message += f"💰 <b>Capital:</b> ${config.total_capital} USDT\n"
                message += f"🎯 <b>Niveles:</b> {config.grid_levels}\n"
                message += f"📈 <b>Rango:</b> ±{config.price_range_percent}%\n"
                message += f"🛡️ <b>Stop-Loss:</b> {getattr(config, 'stop_loss_percent', 5.0)}%\n\n"
                message += f"🚀 Usa /start_bot para iniciar trading con {config_type}"
                bot.send_message(chat_id, message)
            else:
                bot.send_message(chat_id, f"❌ Error activando configuración {config_type}")
                
        except Exception as e:
            self.send_error_message(bot, chat_id, f"activando configuración {config_type}", e)
    
    def handle_update_capital_command(self, chat_id: str, message_text: str, bot):
        """Comando /update_capital X: Actualiza el capital de la configuración activa"""
        try:
            # Obtener configuración activa
            active_config = self.get_user_config(chat_id)
            
            if not active_config:
                bot.send_message(chat_id, "⚠️ No tienes configuración activa\n\nUsa /config para configurar el bot primero.")
                return
            
            # Extraer nuevo capital del mensaje
            parts = message_text.strip().split()
            if len(parts) != 2:
                bot.send_message(
                    chat_id, 
                    "❌ Formato incorrecto.\n\n"
                    "✅ Uso correcto: <code>/update_capital 500</code>\n"
                    "💡 Ejemplo: 500 significa $500 USDT"
                )
                return
            
            try:
                new_capital = float(parts[1])
                if new_capital <= 0:
                    bot.send_message(chat_id, "❌ El capital debe ser mayor a 0")
                    return
            except ValueError:
                bot.send_message(chat_id, "❌ Capital inválido. Usa números como: 500")
                return
            
            # Verificar capital mínimo
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO
            if MODO_PRODUCTIVO:
                capital_minimo = 30 * 10  # 300 USDT mínimo
                if new_capital < capital_minimo:
                    bot.send_message(
                        chat_id,
                        f"❌ Capital insuficiente. Mínimo requerido: ${capital_minimo} USDT\n\n"
                        f"💡 Para 30 niveles se necesita $10 USDT por orden"
                    )
                    return
            
            # Actualizar capital
            config_type = getattr(active_config, 'config_type', 'ETH')
            if self.update_config_capital(chat_id, config_type, new_capital):
                message = f"✅ <b>Capital actualizado exitosamente</b>\n\n"
                message += f"📊 <b>Configuración:</b> {config_type}\n"
                message += f"💰 <b>Nuevo capital:</b> ${new_capital} USDT\n"
                message += f"📈 <b>Par:</b> {active_config.pair}\n\n"
                message += f"🚀 Usa /start_bot para iniciar trading con el nuevo capital"
                bot.send_message(chat_id, message)
            else:
                bot.send_message(chat_id, "❌ Error actualizando capital")
                
        except Exception as e:
            self.send_error_message(bot, chat_id, "actualizando capital", e) 