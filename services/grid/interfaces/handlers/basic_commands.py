"""
Handler para comandos básicos del Grid Bot.
Maneja comandos como start, status, delete_config, etc.
"""
import threading
import time
from datetime import datetime
import asyncio

from shared.services.telegram_bot_service import TelegramBot
from shared.services.logging_config import get_logger
from services.grid.schedulers.multibot_scheduler import (
    get_multibot_scheduler,
    start_multibot_scheduler,
    stop_multibot_scheduler
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
🤖 GRID BOT V3.0 - SISTEMA MULTIBOT AUTÓNOMO

🧠 Arquitectura Inteligente:
• Monitoreo automático de 3 pares simultáneos (ETH, BTC, AVAX)
• El Cerebro decide cuándo operar cada par
• Activación/desactivación automática según condiciones del mercado
• Notificaciones automáticas por Telegram

📱 Comandos Esenciales:

Control del Sistema:
• /start_bot - Inicia el sistema multibot
• /stop_bot - Detiene el sistema multibot
• /status - Estado completo del sistema

Configuración:
• /config - Configurar capital para cada par

Información:
• /balance - Balance y P&L consolidado
• /estado_cerebro - Análisis del cerebro

Modo de Trading:
• /modo_productivo - Cambiar a dinero real
• /modo_sandbox - Cambiar a paper trading

🛡️ SEGURIDAD: El bot inicia en MODO SANDBOX por defecto
💰 Para trading real, usa /modo_productivo manualmente
"""
            
            # Verificar estado actual y modo
            from services.grid.core.cerebro_integration import obtener_configuracion_trading
            trading_config = obtener_configuracion_trading()
            modo_icon = "🟡" if trading_config['modo'] == 'SANDBOX' else "🟢"
            
            scheduler = get_multibot_scheduler()
            if scheduler and scheduler.scheduler.running:
                message += "🟢 Estado Multibot: Ejecutándose\n"
            else:
                message += "🔴 Estado Multibot: Detenido\n"
            
            message += f"{modo_icon} Modo Trading: {trading_config['modo']}\n"
            
            # Verificar si tiene configuración guardada
            user_config = self.get_user_config(chat_id)
            if user_config:
                message += f"⚙️ Configuración: {user_config.pair} con ${user_config.total_capital}\n"
            else:
                message += "⚙️ Configuración: No configurado\n"
            
            message += "\n📋 Comandos principales:\n"
            message += "/config - Configurar capital por par\n"
            message += "/start_bot - Iniciar sistema multibot\n"
            message += "/stop_bot - Detener sistema multibot\n"
            message += "/status - Estado completo del sistema\n"
            message += "/balance - Balance y P&L consolidado\n\n"
            message += "🔄 Control de modo trading:\n"
            message += "/modo_productivo - Cambiar a dinero real ⚠️\n"
            message += "/modo_sandbox - Cambiar a simulación ✅\n\n"
            message += "🧠 Estado del cerebro:\n"
            message += "/estado_cerebro - Ver análisis del cerebro\n"
            
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
            
            # Verificar estado del multibot
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()
            
            if status['total_active_bots'] > 0:
                bot.send_message(chat_id, "⚠️ El multibot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            if not status['scheduler_running']:
                message = "⚠️ Servicio no está listo\n\n"
                message += "El scheduler no está activo. Contacta al administrador."
                bot.send_message(chat_id, message)
                return
            
            # Iniciar bot manualmente
            def start_bot_async():
                try:
                    # Consultar al cerebro por el estado inicial (solo una vez)
                    bot.send_message(chat_id, "🧠 Consultando estado del Cerebro...")
                    
                    # Declarar results fuera del try para que esté disponible más adelante
                    results = {}
                    resultado_batch = None
                    
                    try:
                        import httpx
                        import asyncio
                        cerebro_url = "http://localhost:8004/grid/batch/init"
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            response = loop.run_until_complete(
                                asyncio.wait_for(
                                    httpx.AsyncClient().get(cerebro_url, timeout=60.0),
                                    timeout=60.0
                                )
                            )
                            if response.status_code == 200:
                                resultado_batch = response.json()
                            else:
                                bot.send_message(chat_id, f"⚠️ Error consultando batch inicial del cerebro: {response.status_code}")
                                resultado_batch = None
                        except asyncio.TimeoutError:
                            bot.send_message(
                                chat_id,
                                f"⏰ El cerebro está tardando en responder (timeout 60s)\nContinuando en modo standalone..."
                            )
                            resultado_batch = None
                        except Exception as e:
                            bot.send_message(
                                chat_id,
                                f"⚠️ Error consultando batch inicial del cerebro: {str(e)}\nContinuando en modo standalone..."
                            )
                            resultado_batch = None
                        # Procesar resultado batch
                        if resultado_batch and resultado_batch.get('status') == 'success':
                            results = resultado_batch.get('results', {})
                            from services.grid.core.cerebro_integration import obtener_configuraciones_bd
                            configs = obtener_configuraciones_bd(chat_id)
                            # Ya no mostramos el resumen aquí - se mostrará al final
                        else:
                            bot.send_message(chat_id, "⚠️ No se pudo obtener el estado batch inicial del cerebro. Continuando en modo standalone...")
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"⚠️ No se pudo consultar al Cerebro: {str(e)}\nEl cerebro puede estar tardando en responder.\nContinuando en modo standalone..."
                        )
                    # SEGUNDO: Iniciar el multibot
                    bot.send_message(chat_id, "🚀 Iniciando Multibot...")
                    success = start_multibot_scheduler()
                    # Esperar unos segundos para que las órdenes se creen
                    time.sleep(3)
                    # Consultar estado actualizado del scheduler
                    try:
                        scheduler = get_multibot_scheduler()
                        bot_status = scheduler.get_status()
                        active_bots = bot_status.get('active_bots', [])
                        # Enviar mensajes detallados por par (solo una vez, después de crear órdenes)
                        for active_bot in active_bots:
                            pair = active_bot.get('pair')
                            config = next((c for c in configs if c['pair'] == pair), None)
                            if not config:
                                continue
                            capital = config['total_capital']
                            decision = active_bot.get('last_decision', 'NO_DECISION')
                            indicadores = active_bot.get('indicadores', {}) if 'indicadores' in active_bot else {}
                            razon = active_bot.get('razon', '') if 'razon' in active_bot else ''
                            ordenes_creadas = active_bot.get('ordenes_creadas')
                            ordenes_totales = active_bot.get('ordenes_totales', config.get('grid_levels'))
                            if decision == 'OPERAR_GRID':
                                start_message = f"🚀 <b>GRID BOT AUTORIZADO</b>\n\n"
                                start_message += f"📊 Par: {pair}\n"
                                start_message += f"💰 Capital: ${capital:,.2f}\n"
                                start_message += f"🎯 Niveles: {config['grid_levels']}\n"
                                start_message += f"📈 Rango: {config['price_range_percent']}%\n"
                                start_message += f"📈 ADX: {indicadores.get('adx_actual', 0):.2f}\n"
                                start_message += f"📊 Volatilidad: {indicadores.get('volatilidad_actual', 0):.4f}\n"
                                start_message += f"💬 Sentimiento: {indicadores.get('sentiment_promedio', 0):.3f}\n\n"
                                start_message += f"✅ <b>Razón de autorización:</b>\n"
                                start_message += f"• {razon}\n\n"
                                start_message += f"🟢 El bot está operando automáticamente"
                                if ordenes_creadas is not None and ordenes_totales is not None:
                                    start_message += f"\n📦 Órdenes creadas: {ordenes_creadas}/{ordenes_totales}"
                                elif ordenes_totales is not None:
                                    start_message += f"\n📦 Órdenes creadas: ?/{ordenes_totales}"
                                bot.send_message(chat_id, start_message)
                            elif decision == 'PAUSAR_GRID':
                                pause_message = f"⏸️ <b>GRID BOT PAUSADO</b>\n\n"
                                pause_message += f"📊 Par: {pair}\n"
                                pause_message += f"💰 Capital: ${capital:,.2f}\n"
                                pause_message += f"🎯 Niveles: {config['grid_levels']}\n"
                                pause_message += f"📈 Rango: {config['price_range_percent']}%\n"
                                pause_message += f"📈 ADX: {indicadores.get('adx_actual', 0):.2f}\n"
                                pause_message += f"📊 Volatilidad: {indicadores.get('volatilidad_actual', 0):.4f}\n"
                                pause_message += f"💬 Sentimiento: {indicadores.get('sentiment_promedio', 0):.3f}\n\n"
                                pause_message += f"🛑 <b>Razón de pausa:</b>\n"
                                pause_message += f"• {razon}\n\n"
                                pause_message += f"🔄 El bot se reactivará automáticamente cuando el Cerebro autorice"
                                if ordenes_creadas is not None and ordenes_totales is not None:
                                    pause_message += f"\n📦 Órdenes creadas: {ordenes_creadas}/{ordenes_totales}"
                                elif ordenes_totales is not None:
                                    pause_message += f"\n📦 Órdenes creadas: ?/{ordenes_totales}"
                                bot.send_message(chat_id, pause_message)
                    except Exception as e:
                        logger.warning(f"No se pudo enviar mensajes detallados por par: {e}")
                    
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
                            # MODO SANDBOX: Mostrar configuraciones reales de BD
                            try:
                                from services.grid.core.cerebro_integration import obtener_configuraciones_bd
                                configs = obtener_configuraciones_bd(chat_id)
                                
                                if configs:
                                    # Obtener decisiones del cerebro para cada par
                                    try:
                                        # Usar los resultados del batch inicial si están disponibles
                                        if 'results' in locals() and results:
                                            decisiones_cerebro = results
                                        else:
                                            from services.grid.core.cerebro_integration import consultar_y_procesar_cerebro_batch
                                            decisiones_cerebro = consultar_y_procesar_cerebro_batch()
                                    except Exception as e:
                                        logger.warning(f"⚠️ Error obteniendo decisiones del cerebro: {e}")
                                        decisiones_cerebro = {}
                                    
                                    message = f"🚀 ¡Grid Bot iniciado exitosamente!\n\n"
                                    message += f"🟡 MODO SANDBOX (Paper Trading)\n\n"
                                    message += f"📊 Estado de Configuraciones ({len(configs)} pares):\n"
                                    
                                    for config in configs:
                                        pair = config['pair']
                                        capital = config['total_capital']
                                        
                                        # Obtener decisión del cerebro para este par
                                        decision_data = decisiones_cerebro.get(pair, {}) if decisiones_cerebro else {}
                                        decision = decision_data.get('decision', 'NO_DECISION') if decision_data.get('success', False) else 'NO_DECISION'
                                        
                                        # Determinar icono y estado según decisión del cerebro
                                        if decision == 'OPERAR_GRID':
                                            icon = "🟢"
                                            estado = "Operando"
                                        elif decision == 'PAUSAR_GRID':
                                            icon = "🔴"
                                            estado = "Pausado (Cerebro)"
                                        else:
                                            icon = "🟡"
                                            estado = "Standby"
                                        
                                        message += f"• {icon} {pair}: ${capital:,.2f} | {estado}\n"
                                    
                                    # Contar estados
                                    operando = sum(1 for config in configs 
                                                 if decisiones_cerebro.get(config['pair'], {}).get('success', False) and
                                                 decisiones_cerebro.get(config['pair'], {}).get('decision') == 'OPERAR_GRID')
                                    pausado = sum(1 for config in configs 
                                                if decisiones_cerebro.get(config['pair'], {}).get('success', False) and
                                                decisiones_cerebro.get(config['pair'], {}).get('decision') == 'PAUSAR_GRID')
                                    standby = len(configs) - operando - pausado
                                    
                                    message += f"\n📈 Resumen:\n"
                                    message += f"🟢 Operando: {operando} par{'es' if operando != 1 else ''}\n"
                                    message += f"🔴 Pausado: {pausado} par{'es' if pausado != 1 else ''}\n"
                                    message += f"🟡 Standby: {standby} par{'es' if standby != 1 else ''}\n"
                                    
                                    message += f"\n🛡️ Protecciones V2:\n"
                                    message += f"• Stop-Loss: ✅ (5.0%)\n"
                                    message += f"• Trailing Up: ✅ (Optimiza ganancias)\n\n"
                                    message += f"📈 Usa /status para monitorear el progreso."
                                    
                                    # Agregar separador antes del resumen
                                    bot.send_message(chat_id, message)
                                else:
                                    message = f"🚀 ¡Grid Bot iniciado exitosamente!\n\n"
                                    message += f"🟡 MODO SANDBOX (Paper Trading)\n\n"
                                    message += f"⚠️ Sin configuraciones activas\n"
                                    message += f"Usa /config para configurar los pares\n\n"
                                    message += f"🛡️ Protecciones V2:\n"
                                    message += f"• Stop-Loss: ✅ (5.0%)\n"
                                    message += f"• Trailing Up: ✅ (Optimiza ganancias)\n\n"
                                    message += f"📈 Usa /status para monitorear el progreso."
                                    
                                    # Agregar separador antes del resumen
                                    bot.send_message(chat_id, message)
                            except Exception as e:
                                logger.warning(f"⚠️ Error obteniendo configuraciones de BD: {e}")
                                message = f"🚀 ¡Grid Bot iniciado exitosamente!\n\n"
                                message += f"🟡 MODO SANDBOX (Paper Trading)\n\n"
                                message += f"⚠️ Sin configuraciones activas\n"
                                message += f"Usa /config para configurar los pares\n\n"
                                message += f"🛡️ Protecciones V2:\n"
                                message += f"• Stop-Loss: ✅ (5.0%)\n"
                                message += f"• Trailing Up: ✅ (Optimiza ganancias)\n\n"
                                message += f"📈 Usa /status para monitorear el progreso."
                                
                                # Agregar separador antes del resumen
                                bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, "❌ Error iniciando multibot")
                    
                except Exception as e:
                    self.send_error_message(bot, chat_id, "start_bot_async", e)
            
            threading.Thread(target=start_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "start_bot", e)
    
    def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /stop_bot - V2 con modo manual"""
        try:
            # Verificar estado del multibot
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()
            
            if status['total_active_bots'] == 0:
                bot.send_message(chat_id, "ℹ️ El multibot ya está detenido (modo standby).")
                return
            
            if not status['scheduler_running']:
                message = "⚠️ <b>No se puede detener el multibot</b>\n\n"
                message += "El scheduler no está activo."
                bot.send_message(chat_id, message)
                return
            
            def stop_bot_async():
                try:
                    success = stop_multibot_scheduler()
                    
                    if success:
                        message = "🛑 <b>Multibot detenido correctamente</b>\n\n"
                        message += "✅ Se señaló la parada del multibot\n"
                        message += "🧹 Las órdenes serán canceladas automáticamente\n"
                        message += "⏸️ Multibot entrando en modo standby\n\n"
                        message += "ℹ️ <i>El proceso de cancelación puede tomar unos segundos</i>\n"
                        message += "▶️ Usa /start_bot para reanudar trading"
                        bot.send_message(chat_id, message)
                    else:
                        bot.send_message(chat_id, "❌ <b>Error deteniendo multibot</b>")
                        
                except Exception as e:
                    self.send_error_message(bot, chat_id, "stop_bot_async", e)
            
            threading.Thread(target=stop_bot_async, daemon=True).start()
            bot.send_message(chat_id, "⏳ Deteniendo Grid Bot...")
            
        except Exception as e:
            self.send_error_message(bot, chat_id, "stop_bot", e)
    
    def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """
        Comando /status: Muestra estado del grid bot con integración Cerebro
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO, estado_cerebro, obtener_configuracion_trading
            
            # Obtener estado del scheduler
            scheduler = get_multibot_scheduler()
            is_running = scheduler.scheduler.running if scheduler else False
            
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
                # MODO SANDBOX: Usar configuraciones de la base de datos
                try:
                    from services.grid.core.cerebro_integration import obtener_configuraciones_bd
                    configs = obtener_configuraciones_bd(chat_id)
                    
                    if configs:
                        status_message = f"""
🤖 ESTADO DEL GRID BOT

🟡 MODO SANDBOX (Paper Trading)

📊 Configuraciones Activas ({len(configs)} pares):
"""
                        for config in configs:
                            decision_icon = "🟢" if config['last_decision'] == 'OPERAR_GRID' else "🔴"
                            running_icon = "🟢" if config['is_running'] else "🔴"
                            status_message += f"• {config['pair']}: ${config['total_capital']:,.2f} | {decision_icon} {config['last_decision']} | {running_icon} {'Ejecutando' if config['is_running'] else 'Pausado'}\n"
                        
                        status_message += f"""
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
                    else:
                        status_message = f"""
🤖 ESTADO DEL GRID BOT

🟡 MODO SANDBOX (Paper Trading)

⚠️ Sin configuraciones activas
Usa /config para configurar los pares

🔄 Estado del Sistema:
• Scheduler: {'🟢 Activo' if is_running else '🔴 Inactivo'}
• Modo Trading: {config_trading.get('modo', 'No disponible')}
• Modo Operación: 🧠 AUTÓNOMO (Responde a decisiones del Cerebro)

🧠 Estado del Cerebro:
• Decisión: {cerebro_estado.get('decision', 'No disponible')}
• Fuente: {cerebro_estado.get('fuente', 'No disponible')}
• Última actualización: {cerebro_estado.get('ultima_actualizacion', 'No disponible')}
"""
                except Exception as e:
                    logger.warning(f"⚠️ Error obteniendo configuraciones de BD: {e}")
                    status_message = f"""
🤖 ESTADO DEL GRID BOT

🟡 MODO SANDBOX (Paper Trading)

📊 Configuración Fija (fallback):
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

    def handle_modo_productivo_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_productivo: Cambia a modo productivo (trading real)
        """
        try:
            from services.grid.core.cerebro_integration import MODO_PRODUCTIVO, alternar_modo_trading, obtener_configuracion_trading
            from services.grid.schedulers.multibot_scheduler import get_multibot_scheduler
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()

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

            # Si el multibot está corriendo, detenerlo
            if status['total_active_bots'] > 0:
                bot.send_message(chat_id, "🛑 Deteniendo Multibot por cambio de modo...")
                scheduler.stop_all_bots()
                bot.send_message(chat_id, "✅ Multibot detenido correctamente.")

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
            bot.send_message(chat_id, "🚀 Reiniciando Multibot en modo PRODUCTIVO...")
            scheduler.start()

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
            from services.grid.schedulers.multibot_scheduler import get_multibot_scheduler
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()

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

            # Si el multibot está corriendo, detenerlo
            if status['total_active_bots'] > 0:
                bot.send_message(chat_id, "🛑 Deteniendo Multibot por cambio de modo...")
                scheduler.stop_all_bots()
                bot.send_message(chat_id, "✅ Multibot detenido correctamente.")

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
            bot.send_message(chat_id, "🚀 Reiniciando Multibot en modo SANDBOX...")
            scheduler.start()

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
                
                # Verificar que el multibot esté ejecutándose para obtener balance real
                scheduler = get_multibot_scheduler()
                status = scheduler.get_status()
                if status['total_active_bots'] == 0:
                    bot.send_message(chat_id, "⚠️ El multibot no está ejecutándose\n\nUsa /start_bot para iniciar el trading y poder ver el balance actual.")
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

 