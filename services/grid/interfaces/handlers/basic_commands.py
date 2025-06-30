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
🤖 **GRID BOT V3.0 - MODO AUTÓNOMO**

🧠 **Nueva Arquitectura Inteligente:**
• El Grid responde automáticamente a las decisiones del Cerebro
• Monitoreo continuo cada 10 minutos
• Activación/desactivación automática según condiciones del mercado

📱 **Comandos Disponibles:**

**Configuración:**
• /config - Configurar parámetros del bot
• /info_config - Ver configuración actual
• /delete_config - Eliminar configuración

**Control Manual:**
• /start_bot - Iniciar trading manualmente (consulta al cerebro)
• /stop_bot - Detener trading manualmente
• /restart_bot - Reiniciar bot
• /status - Estado actual del sistema

**Modo de Trading:**
• /modo_productivo - Cambiar a trading real
• /modo_sandbox - Cambiar a paper trading
• /modo_actual - Ver modo actual

**Información del Cerebro:**
• /estado_cerebro - Ver análisis detallado del cerebro

🔄 **Funcionamiento Autónomo:**
• El Cerebro analiza el mercado cada 2 horas
• Si autoriza trading → Grid se activa automáticamente
• Si recomienda pausar → Grid se detiene automáticamente
• Notificaciones automáticas por Telegram

💡 **Uso Recomendado:**
1. Configura con /config
2. El sistema funciona automáticamente
3. Usa /status para monitorear
4. Interviene solo si necesitas cambiar estrategia
"""
            
            # Verificar estado actual y modo
            from services.grid.main import obtener_configuracion_trading
            trading_config = obtener_configuracion_trading()
            modo_icon = "🟡" if trading_config['modo'] == 'SANDBOX' else "🟢"
            
            scheduler = get_grid_scheduler()
            if scheduler and scheduler.running:
                message += "🟢 <b>Estado Bot:</b> Ejecutándose\n"
            else:
                message += "🔴 <b>Estado Bot:</b> Detenido\n"
            
            message += f"{modo_icon} <b>Modo Trading:</b> {trading_config['modo']}\n"
            
            # Verificar si tiene configuración guardada
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"⚙️ <b>Configuración:</b> {user_config.pair} con ${user_config.total_capital}\n"
            else:
                message += "⚙️ <b>Configuración:</b> No configurado\n"
            
            message += "\n📋 <b>Comandos principales:</b>\n"
            message += "/config - Configurar bot (solo par + capital)\n"
            message += "/start_bot - Iniciar trading inteligente\n"
            message += "/stop_bot - Detener bot\n"
            message += "/status - Estado completo (bot + cerebro)\n\n"
            message += "🔄 <b>Control de modo trading:</b>\n"
            message += "/modo_productivo - Cambiar a dinero real ⚠️\n"
            message += "/modo_sandbox - Cambiar a simulación ✅\n"
            message += "/modo_actual - Ver modo activo\n\n"
            message += "🧠 <b>Estado del cerebro:</b>\n"
            message += "/estado_cerebro - Ver análisis del cerebro\n\n"
            message += "🛡️ <b>Protecciones:</b>\n"
            message += "/protections - Ver estado stop-loss\n"
            message += "/set_stop_loss X - Configurar % stop-loss\n\n"
            message += "📊 <b>Información:</b>\n"
            message += "/info_config - Info sobre configuración optimizada\n"
            
            bot.send_message(chat_id, message)
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "comando start", e)
    
    def handle_start_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start_bot - V2 con modo manual"""
        try:
            # Verificar configuración
            user_config = self.get_user_config(chat_id)
            if not user_config:
                message = "⚠️ <b>No tienes configuración guardada</b>\n\n"
                message += "Usa /config para configurar el bot primero."
                bot.send_message(chat_id, message)
                return
            
            # Verificar estado del bot
            bot_status = get_grid_bot_status()
            if bot_status['bot_running']:
                bot.send_message(chat_id, "⚠️ El bot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            if not bot_status['ready_to_start']:
                message = "⚠️ <b>Servicio no está listo</b>\n\n"
                message += "El scheduler no está activo. Contacta al administrador."
                bot.send_message(chat_id, message)
                return
            
            # Iniciar bot manualmente
            def start_bot_async():
                try:
                    # PRIMERO: Consultar estado del cerebro
                    bot.send_message(chat_id, "🧠 Consultando estado del Cerebro...")
                    
                    try:
                        from services.grid.main import consultar_estado_inicial_cerebro
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
                                    f"🧠 <b>Estado del Cerebro:</b>\n"
                                    f"• Decisión: {decision_cerebro}\n"
                                    f"• Razón: {resultado_cerebro.get('razon', 'No disponible')}\n"
                                    f"• {mensaje_cerebro}"
                                )
                                
                                # Si el cerebro dice PAUSAR, preguntar si continuar
                                if not resultado_cerebro.get('puede_operar', False):
                                    bot.send_message(
                                        chat_id,
                                        "⚠️ <b>El Cerebro recomienda pausar el trading</b>\n\n"
                                        "¿Deseas continuar de todas formas?\n"
                                        "Responde 'SI' para continuar o 'NO' para cancelar."
                                    )
                                    # Aquí podrías implementar un sistema de confirmación
                                    # Por ahora, continuamos con advertencia
                                    bot.send_message(chat_id, "⚠️ Continuando con advertencia...")
                            else:
                                bot.send_message(
                                    chat_id,
                                    f"⚠️ <b>Respuesta inesperada del Cerebro:</b> {resultado_cerebro}\n"
                                    f"Continuando en modo standalone..."
                                )
                            
                        finally:
                            loop.close()
                            
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"⚠️ <b>No se pudo consultar al Cerebro:</b> {str(e)}\n"
                            f"Continuando en modo standalone..."
                        )
                    
                    # SEGUNDO: Iniciar el grid bot
                    bot.send_message(chat_id, "🚀 Iniciando Grid Bot...")
                    success, result_message = start_grid_bot_manual()
                    
                    if success:
                        message = f"🚀 <b>¡Grid Bot iniciado exitosamente!</b>\n\n"
                        message += f"📊 <b>Trading:</b> {user_config.pair}\n"
                        message += f"💰 <b>Capital:</b> ${user_config.total_capital} USDT\n"
                        message += f"🎚️ <b>Niveles:</b> {user_config.grid_levels}\n"
                        message += f"📊 <b>Rango:</b> ±{user_config.price_range_percent}%\n\n"
                        message += f"🛡️ <b>Protecciones V2:</b>\n"
                        message += f"• Stop-Loss: {'✅' if getattr(user_config, 'enable_stop_loss', True) else '❌'} ({getattr(user_config, 'stop_loss_percent', 5.0)}%)\n"
                        message += f"• Trailing Up: {'✅' if getattr(user_config, 'enable_trailing_up', True) else '❌'}\n\n"
                        message += f"📈 Usa /status para monitorear el progreso."
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, f"❌ <b>Error iniciando bot:</b> {result_message}")
                        
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
            # Obtener configuración del usuario
            user_config = self.get_user_config(chat_id)
            
            # Obtener estado del scheduler
            scheduler = get_grid_scheduler()
            is_running = scheduler.running if scheduler else False
            
            # Obtener estado del cerebro y modo de trading
            try:
                from services.grid.main import estado_cerebro, obtener_configuracion_trading
                cerebro_estado = estado_cerebro
                config_trading = obtener_configuracion_trading()
            except ImportError:
                cerebro_estado = {"decision": "No disponible", "fuente": "error"}
                config_trading = {"modo": "No disponible"}
            
            # Crear mensaje de estado completo
            if user_config:
                status_message = f"""
🤖 **ESTADO DEL GRID BOT**

📊 **Configuración Activa:**
• Par: {user_config.pair}
• Capital: ${user_config.total_capital:,.2f}
• Niveles: {user_config.grid_levels}
• Rango: {user_config.price_range_percent}%

🔄 **Estado del Sistema:**
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• **Modo Operación: 🧠 AUTÓNOMO** (Responde a decisiones del Cerebro)

🧠 **Estado del Cerebro:**
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}

⚡ **Protecciones Avanzadas:**
• Stop Loss: {'🟢 Activo' if getattr(user_config, 'enable_stop_loss', False) else '🔴 Inactivo'}
• Trailing Up: {'🟢 Activo' if getattr(user_config, 'enable_trailing_up', False) else '🔴 Inactivo'}
"""
                
                if hasattr(user_config, 'enable_stop_loss') and getattr(user_config, 'enable_stop_loss', False):
                    status_message += f"• Stop Loss %: {getattr(user_config, 'stop_loss_percent', 5.0)}%\n"
            else:
                status_message = f"""
🤖 **ESTADO DEL GRID BOT**

⚠️ **Sin configuración activa**
Usa /config para configurar el bot

🔄 **Estado del Sistema:**
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• **Modo Operación: 🧠 AUTÓNOMO** (Responde a decisiones del Cerebro)

🧠 **Estado del Cerebro:**
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}
"""
            
            # Agregar comandos disponibles
            status_message += """

📝 **Comandos Nuevos:**
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
            from services.grid.main import MODO_PRODUCTIVO, alternar_modo_trading, obtener_configuracion_trading
            from services.grid.schedulers.grid_scheduler import get_grid_bot_status, stop_grid_bot_manual, start_grid_bot_manual

            bot_status = get_grid_bot_status()
            if MODO_PRODUCTIVO:
                config = obtener_configuracion_trading()
                message = f"""
🟢 **YA EN MODO PRODUCTIVO**

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

⚠️ **ADVERTENCIA**: Trading con dinero real
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
🟢 **CAMBIADO A MODO PRODUCTIVO**

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

⚠️ **ADVERTENCIA IMPORTANTE**:
Ahora estás operando con DINERO REAL en Binance.
Todas las operaciones afectarán tu cuenta real.

🔄 Usa /modo_sandbox para volver a paper trading
"""
            bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_productivo ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            bot.send_message(chat_id, "🚀 Reiniciando Grid Bot en modo PRODUCTIVO...")
            success, msg = start_grid_bot_manual()
            if success:
                bot.send_message(chat_id, "✅ Grid Bot iniciado en modo PRODUCTIVO.")
            else:
                bot.send_message(chat_id, f"⚠️ No se pudo iniciar el bot automáticamente: {msg}")

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo productivo: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_productivo_command: {e}")

    def handle_modo_sandbox_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_sandbox: Cambia a modo sandbox (paper trading)
        """
        try:
            from services.grid.main import MODO_PRODUCTIVO, alternar_modo_trading, obtener_configuracion_trading
            from services.grid.schedulers.grid_scheduler import get_grid_bot_status, stop_grid_bot_manual, start_grid_bot_manual

            bot_status = get_grid_bot_status()
            if not MODO_PRODUCTIVO:
                config = obtener_configuracion_trading()
                message = f"""
🟡 **YA EN MODO SANDBOX**

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

✅ **SEGURO**: Paper trading sin riesgo
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
🟡 **CAMBIADO A MODO SANDBOX**

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

✅ **MODO SEGURO ACTIVADO**:
Todas las operaciones son simuladas.
No se usa dinero real.

🔄 Usa /modo_productivo para trading real
"""
            bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_sandbox ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            bot.send_message(chat_id, "🚀 Reiniciando Grid Bot en modo SANDBOX...")
            success, msg = start_grid_bot_manual()
            if success:
                bot.send_message(chat_id, "✅ Grid Bot iniciado en modo SANDBOX.")
            else:
                bot.send_message(chat_id, f"⚠️ No se pudo iniciar el bot automáticamente: {msg}")

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo sandbox: {str(e)}"
            bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_sandbox_command: {e}")

    def handle_estado_cerebro_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /estado_cerebro: Muestra estado detallado del cerebro
        """
        try:
            from services.grid.main import estado_cerebro
            
            message = f"""
🧠 **ESTADO DETALLADO DEL CEREBRO**

📊 **Decisión Actual:**
• Acción: {estado_cerebro.get('decision', 'No disponible')}
• Fuente: {estado_cerebro.get('fuente', 'No disponible')}
• Última actualización: {estado_cerebro.get('ultima_actualizacion', 'No disponible')}

🔄 **Significado de las decisiones:**
• OPERAR_GRID: Condiciones favorables para trading
• PAUSAR_GRID: Condiciones desfavorables, pausa recomendada

📡 **Integración:**
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
            from services.grid.main import obtener_configuracion_trading
            
            config = obtener_configuracion_trading()
            modo_icon = "🟢" if config['modo'] == "PRODUCTIVO" else "🟡"
            
            message = f"""
{modo_icon} **MODO DE TRADING ACTUAL**

• Modo: {config['modo']}
• Descripción: {config['descripcion']}

💡 **Comandos disponibles:**
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
            from services.grid.main import obtener_configuracion_trading
            
            config = obtener_configuracion_trading()
            modo_icon = "🟢" if config['modo'] == "PRODUCTIVO" else "🟡"
            
            # Calcular capital mínimo para 30 niveles
            capital_minimo = 30 * 25  # 750 USDT
            
            message = f"""
📊 **CONFIGURACIÓN OPTIMIZADA v3.0**

🎯 **Parámetros actuales (FIJOS):**
• Niveles de grid: 30 (óptimo validado)
• Rango de precios: 10% (óptimo validado)
• Capital sandbox: $1000 USDT (fijo)
• Capital productivo mínimo: ${capital_minimo} USDT

🧠 **Integración con Cerebro:**
• ADX < 30: Condiciones favorables
• Volatilidad > 4%: Mercado activo
• Stop-loss automático: 5% por defecto
• Trailing: Desactivado (Cerebro decide)

{modo_icon} **Modo actual: {config['modo']}**

💰 **¿Por qué ${capital_minimo} USDT mínimo?**
• 30 niveles requieren diversificación
• ~$25 USDT por nivel para cubrir comisiones
• Comisiones Binance: 0.1% por trade
• Spread entre compra/venta
• Fluctuaciones del 10% de rango
• Liquidez para recompras

🔄 **Evolución del sistema:**

📈 **VERSIÓN ACTUAL (v3.0):**
• Parámetros fijos: 30 niveles, 10% rango
• Cerebro decide: ¿Cuándo operar?
• Configuración: Solo par + capital

🚀 **VERSIÓN FUTURA (v4.0):**
• Cerebro decide: ¿Cuándo operar?
• Cerebro decide: ¿Cuántos niveles? (dinámico)
• Cerebro decide: ¿Qué rango usar? (dinámico)
• Configuración: Solo par + capital mínimo

🧠 **Cerebro Inteligente Futuro:**
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