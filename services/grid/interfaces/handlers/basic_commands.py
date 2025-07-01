"""
Handler para comandos básicos del Grid Bot.
Maneja comandos como start, status, delete_config, etc.
"""
import threading
import time
from datetime import datetime
import asyncio
import html

from shared.services.telegram_bot_service import TelegramBot
from shared.services.logging_config import get_logger
from services.grid.schedulers.multibot_scheduler import (
    get_multibot_scheduler,
    start_multibot_scheduler,
    stop_multibot_scheduler
)
from services.grid.core.trading_mode_manager import trading_mode_manager
from services.grid.core.cerebro_integration import cerebro_client
from services.grid.data.config_repository import get_all_active_configs_for_user
from .base_handler import BaseHandler

logger = get_logger(__name__)


class BasicCommandsHandler(BaseHandler):
    """Handler para comandos básicos del Grid Bot"""
    
    async def handle_start_command(self, chat_id: str, message_text: str, bot: TelegramBot):
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
            trading_config = trading_mode_manager.get_config()
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
            
            await bot.send_message(chat_id, message)
            
        except Exception as e:
            await self.send_error_message(bot, chat_id, "comando start", e)
    
    async def handle_start_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /start_bot - V2 con modo manual"""
        try:
            is_productive = trading_mode_manager.is_productive()
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if is_productive:
                # MODO PRODUCTIVO: Requiere configuración guardada
                user_config = self.get_user_config(chat_id)
                if not user_config:
                    message = "⚠️ No tienes configuración guardada\n\n"
                    message += "Usa /config para configurar el bot primero."
                    await bot.send_message(chat_id, message)
                    return
            else:
                # MODO SANDBOX: Usar configuración fija
                user_config = None  # No necesitamos config de BD en sandbox
            
            # Verificar estado del multibot
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()
            
            if status['total_active_bots'] > 0:
                await bot.send_message(chat_id, "⚠️ El multibot ya está ejecutándose. Usa /stop_bot para detenerlo primero.")
                return
            
            if not status['scheduler_running']:
                message = "⚠️ Servicio no está listo\n\n"
                message += "El scheduler no está activo. Contacta al administrador."
                await bot.send_message(chat_id, message)
                return

            await bot.send_message(chat_id, "⏳ Iniciando Grid Bot...")
            
            # Iniciar bot manualmente en una tarea de fondo para no bloquear al bot de telegram
            asyncio.create_task(self._start_bot_async(chat_id, bot, is_productive, user_config))

        except Exception as e:
            await self.send_error_message(bot, chat_id, "start_bot", e)

    async def _start_bot_async(self, chat_id, bot, is_productive, user_config):
        try:
            scheduler = get_multibot_scheduler()

            # Forzar limpieza de estado antes de iniciar para evitar race conditions
            logger.info("🧹 Forzando limpieza de estado del scheduler antes de iniciar...")
            scheduler.force_stop_and_clear_all()
            await asyncio.sleep(1)  # Dar un momento para que los hilos antiguos terminen la limpieza

            # 1. Asegurarse de que el scheduler general esté corriendo
            if not scheduler.scheduler.running:
                scheduler.start()
            
            # 2. Consultar las decisiones del Cerebro para todos los pares
            await bot.send_message(chat_id, "🧠 Consultando decisiones del Cerebro para todos los pares...")
            decisiones = await cerebro_client.consultar_y_procesar_batch()

            if not decisiones:
                await bot.send_message(chat_id, "⚠️ No se pudo obtener el estado inicial del cerebro. No se iniciará ningún bot.")
                return

            # 3. Obtener las configuraciones del usuario
            configs = get_all_active_configs_for_user(chat_id)
            if not configs:
                await bot.send_message(chat_id, "⚠️ No tienes configuraciones activas. Usa /config para configurar los pares.")
                return

            # 4. Iniciar/pausar bots y recopilar información para el resumen
            bots_iniciados = []
            bots_pausados = []

            for config in configs:
                pair = config['pair']
                decision_data = decisiones.get(pair)

                if decision_data and decision_data.get('decision') == 'OPERAR_GRID':
                    success = scheduler.start_bot_for_pair(pair, config)
                    if success:
                        bots_iniciados.append({'config': config, 'data': decision_data})
                    else:
                        logger.warning(f"Fallo al iniciar bot para {pair} (posiblemente ya activo)")
                else:
                    bots_pausados.append({'config': config, 'data': decision_data})
            
            # 5. Resumen final unificado y detallado
            trading_config = trading_mode_manager.get_config()
            modo_icon = "🟢" if trading_config['modo'] == 'PRODUCTIVO' else "🟡"
            
            summary_message = f"🤖   <b>GRID BOT - INICIO DEL SISTEMA</b>   🤖\n"
            summary_message += "--------------------------------------\n"
            summary_message += f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            summary_message += f"<b>MODO DE OPERACIÓN:</b> {modo_icon} {trading_config['modo']}\n"
            summary_message += "--------------------------------------\n\n"
            
            summary_message += "<b>ANÁLISIS DEL CEREBRO COMPLETADO</b>\n"
            summary_message += "El sistema ha evaluado las condiciones del mercado y ha tomado las siguientes decisiones:\n\n"

            icon_map = {'ETH': '💎', 'BTC': '🟠', 'AVAX': '🔴'}

            if bots_iniciados:
                summary_message += f"🚀 <b>Bots Autorizados para Trading:</b> ({len(bots_iniciados)} bots)\n"
                summary_message += "<i>(Estos bots comenzarán a operar inmediatamente)</i>\n\n"
                for bot_info in bots_iniciados:
                    config = bot_info['config']
                    data = bot_info['data']
                    indicadores = data.get('indicadores', {})
                    pair = config['pair']
                    crypto_symbol = pair.split('/')[0]
                    icon = icon_map.get(crypto_symbol, '🪙')

                    summary_message += f"  • {icon} <b>{pair}</b>\n"
                    summary_message += f"    - <b>Capital:</b> ${config['total_capital']:,.2f}\n"
                    summary_message += f"    - <b>Decisión:</b> {data.get('decision', 'N/A')}\n"
                    summary_message += f"    - <b>Razón:</b> <i>{html.escape(data.get('razon', 'N/A'))}</i>\n"
                    if indicadores:
                        summary_message += f"    - <b>Indicadores:</b> <pre>ADX: {indicadores.get('adx_actual', 0):.2f}, Vol: {indicadores.get('volatilidad_actual', 0):.4f}, Sent: {indicadores.get('sentiment_promedio', 0):.3f}</pre>\n"
                summary_message += "\n"

            if bots_pausados:
                summary_message += f"⏸️ <b>Bots en Pausa (Standby):</b> ({len(bots_pausados)} bots)\n"
                summary_message += "<i>(Estos bots permanecerán inactivos hasta que las condiciones mejoren)</i>\n\n"
                for bot_info in bots_pausados:
                    config = bot_info['config']
                    data = bot_info['data']
                    indicadores = data.get('indicadores', {}) if data else {}
                    razon = data.get('razon', 'Sin datos del cerebro') if data else 'Sin datos del cerebro'
                    pair = config['pair']
                    crypto_symbol = pair.split('/')[0]
                    icon = icon_map.get(crypto_symbol, '🪙')
                    
                    summary_message += f"  • {icon} <b>{pair}</b>\n"
                    summary_message += f"    - <b>Capital:</b> ${config['total_capital']:,.2f}\n"
                    summary_message += f"    - <b>Decisión:</b> {data.get('decision', 'PAUSAR_GRID') if data else 'PAUSAR_GRID'}\n"
                    summary_message += f"    - <b>Razón:</b> <i>{html.escape(razon)}</i>\n"
                    if indicadores:
                        summary_message += f"    - <b>Indicadores:</b> <pre>ADX: {indicadores.get('adx_actual', 0):.2f}, Vol: {indicadores.get('volatilidad_actual', 0):.4f}, Sent: {indicadores.get('sentiment_promedio', 0):.3f}</pre>\n"
                summary_message += "\n"

            summary_message += "--------------------------------------\n"
            summary_message += "<b>RESUMEN DEL SISTEMA</b>\n"
            
            total_capital_activo = sum(b['config']['total_capital'] for b in bots_iniciados)
            summary_message += f"• <b>Capital Activo (en trading):</b> ${total_capital_activo:,.2f}\n"

            final_status = scheduler.get_status()
            summary_message += f"• <b>Bots Activos:</b> {final_status['total_active_bots']} / {len(configs)}\n"
            summary_message += "• <b>Próximo Análisis del Cerebro:</b> ~1 hora\n"
            summary_message += "--------------------------------------\n\n"
            
            summary_message += "El sistema está ahora en modo de monitoreo continuo. Recibirás resúmenes de actividad cada 30 minutos.\n\n"
            summary_message += "Usa /status para ver el estado en tiempo real."

            await bot.send_message(chat_id, summary_message)

        except Exception as e:
            await self.send_error_message(bot, chat_id, "start_bot_async", e)

    async def handle_stop_bot_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """Maneja el comando /stop_bot - V2 con modo manual"""
        try:
            # Verificar estado del multibot
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()
            
            if status['total_active_bots'] == 0:
                await bot.send_message(chat_id, "ℹ️ El multibot ya está detenido (modo standby).")
                return
            
            if not status['scheduler_running']:
                message = "⚠️ <b>No se puede detener el multibot</b>\n\n"
                message += "El scheduler no está activo."
                await bot.send_message(chat_id, message)
                return
            
            await bot.send_message(chat_id, "⏳ Deteniendo Grid Bot...")
            asyncio.create_task(self._stop_bot_async(chat_id, bot))

        except Exception as e:
            await self.send_error_message(bot, chat_id, "stop_bot", e)

    async def _stop_bot_async(self, chat_id, bot):
        try:
            scheduler = get_multibot_scheduler()
            scheduler.stop_all_bots()
            success = True # Asumimos éxito, stop_all_bots no retorna valor

            if success:
                message = "🛑 <b>Multibot detenido correctamente</b>\n\n"
                message += "✅ Se señaló la parada de todos los bots activos\n"
                message += "🧹 Las órdenes serán canceladas automáticamente en sus ciclos\n"
                message += "⏸️ El sistema queda en modo standby\n\n"
                message += "ℹ️ <i>El proceso de cancelación puede tomar unos segundos</i>\n"
                message += "▶️ Usa /start_bot para reanudar trading"
                await bot.send_message(chat_id, message)
            else:
                await bot.send_message(chat_id, "❌ <b>Error deteniendo multibot</b>")

        except Exception as e:
            await self.send_error_message(bot, chat_id, "stop_bot_async", e)

    async def handle_status_command(self, chat_id: str, message_text: str, bot: TelegramBot):
        """
        Comando /status: Muestra estado del grid bot con integración Cerebro
        """
        try:
            is_productive = trading_mode_manager.is_productive()
            
            # Obtener estado del scheduler
            scheduler = get_multibot_scheduler()
            is_running = scheduler.scheduler.running if scheduler else False
            
            # Obtener estado del cerebro y modo de trading
            try:
                cerebro_estado = cerebro_client.estado_cerebro
                config_trading = trading_mode_manager.get_config()
            except ImportError:
                cerebro_estado = {"decision": "No disponible", "fuente": "error"}
                config_trading = {"modo": "No disponible"}
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if is_productive:
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
                    configs = get_all_active_configs_for_user(chat_id)
                    
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
            
            await bot.send_message(chat_id, status_message)
            logger.info(f"✅ Estado enviado a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener el estado: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_status_command: {e}")

    async def handle_modo_productivo_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_productivo: Cambia a modo productivo (trading real)
        """
        try:
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()

            if trading_mode_manager.is_productive():
                config = trading_mode_manager.get_config()
                message = f"""
🟢 YA EN MODO PRODUCTIVO

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

⚠️ ADVERTENCIA: Trading con dinero real
"""
                await bot.send_message(chat_id, message)
                return

            # Si el multibot está corriendo, detenerlo
            if status['total_active_bots'] > 0:
                await bot.send_message(chat_id, "🛑 Deteniendo Multibot por cambio de modo...")
                scheduler.stop_all_bots()
                await bot.send_message(chat_id, "✅ Multibot detenido correctamente.")

            # Cambiar a modo productivo
            config = trading_mode_manager.toggle_mode()
            message = f"""
🟢 CAMBIADO A MODO PRODUCTIVO

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

⚠️ ADVERTENCIA IMPORTANTE:
Ahora estás operando con DINERO REAL en Binance.
Todas las operaciones afectarán tu cuenta real.

🔄 Usa /modo_sandbox para volver a paper trading
"""
            await bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_productivo ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            await bot.send_message(chat_id, "🚀 Reiniciando Multibot en modo PRODUCTIVO...")
            scheduler.start()

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo productivo: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_productivo_command: {e}")

    async def handle_modo_sandbox_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /modo_sandbox: Cambia a modo sandbox (paper trading)
        """
        try:
            scheduler = get_multibot_scheduler()
            status = scheduler.get_status()

            if not trading_mode_manager.is_productive():
                config = trading_mode_manager.get_config()
                message = f"""
🟡 YA EN MODO SANDBOX

• Modo actual: {config['modo']}
• Descripción: {config['descripcion']}
• Estado: Activo

✅ SEGURO: Paper trading sin riesgo
"""
                await bot.send_message(chat_id, message)
                return

            # Si el multibot está corriendo, detenerlo
            if status['total_active_bots'] > 0:
                await bot.send_message(chat_id, "🛑 Deteniendo Multibot por cambio de modo...")
                scheduler.stop_all_bots()
                await bot.send_message(chat_id, "✅ Multibot detenido correctamente.")

            # Cambiar a modo sandbox
            config = trading_mode_manager.toggle_mode()
            message = f"""
🟡 CAMBIADO A MODO SANDBOX

• Nuevo modo: {config['modo']}
• Descripción: {config['descripcion']}

✅ MODO SEGURO ACTIVADO:
Todas las operaciones son simuladas.
No se usa dinero real.

🔄 Usa /modo_productivo para trading real
"""
            await bot.send_message(chat_id, message)
            logger.info(f"✅ Comando modo_sandbox ejecutado para chat {chat_id}")

            # Reiniciar el bot automáticamente en el nuevo modo
            await bot.send_message(chat_id, "🚀 Reiniciando Multibot en modo SANDBOX...")
            scheduler.start()

        except Exception as e:
            error_message = f"❌ Error al cambiar a modo sandbox: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_modo_sandbox_command: {e}")

    async def handle_estado_cerebro_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /estado_cerebro: Muestra estado detallado del cerebro
        """
        try:
            estado_cerebro = cerebro_client.estado_cerebro
            
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
            
            await bot.send_message(chat_id, message)
            logger.info(f"✅ Estado del cerebro enviado a chat {chat_id}")
            
        except Exception as e:
            error_message = f"❌ Error al obtener estado del cerebro: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_estado_cerebro_command: {e}")

    async def handle_balance_command(self, chat_id: str, message_text: str, bot):
        """
        Comando /balance: Muestra el balance actual de la cuenta
        MEJORADO: Usa nueva función de P&L con explicación detallada
        """
        try:
            is_productive = trading_mode_manager.is_productive()
            
            # LÓGICA DIFERENTE SEGÚN MODO
            if is_productive:
                # MODO PRODUCTIVO: Requiere configuración guardada
                user_config = self.get_user_config(chat_id)
                if not user_config:
                    await bot.send_message(chat_id, "⚠️ No tienes configuración guardada\n\nUsa /config para configurar el bot primero.")
                    return
                
                # Verificar que el multibot esté ejecutándose para obtener balance real
                scheduler = get_multibot_scheduler()
                status = scheduler.get_status()
                if status['total_active_bots'] == 0:
                    await bot.send_message(chat_id, "⚠️ El multibot no está ejecutándose\n\nUsa /start_bot para iniciar el trading y poder ver el balance actual.")
                    return
                
                pair = str(user_config.pair)
                initial_capital = float(getattr(user_config, 'total_capital', 0))
                
            else:
                # MODO SANDBOX: Usar configuración fija
                pair = 'ETH/USDT'
                initial_capital = 1000.0  # Capital fijo para sandbox
                
                # En sandbox, no necesitamos verificar si el bot está corriendo
                # porque siempre podemos consultar el balance de paper trading
            
            await bot.send_message(chat_id, "⏳ Obteniendo balance actual...")
            asyncio.create_task(self._get_balance_async(chat_id, bot, is_productive, pair, initial_capital))

        except Exception as e:
            error_message = f"❌ Error al obtener balance: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en handle_balance_command: {e}")

    async def _get_balance_async(self, chat_id, bot, is_productive, pair, initial_capital):
        try:
            # Obtener conexión al exchange
            from services.grid.core.config_manager import get_exchange_connection
            exchange = get_exchange_connection()
            
            # Obtener balance actual
            from shared.services.telegram_service import get_current_balance, calculate_pnl_with_explanation
            balance = get_current_balance(exchange, pair)
            
            # Calcular P&L usando nueva función mejorada
            mode = "PRODUCTIVO" if is_productive else "SANDBOX"
            pnl_data = calculate_pnl_with_explanation(balance, initial_capital, mode)
            
            # Crear mensaje con información del modo
            modo_info = "🟢 PRODUCTIVO" if is_productive else "🟡 SANDBOX (Paper Trading)"
            
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
            
            await bot.send_message(chat_id, message)
            logger.info(f"✅ Balance enviado a chat {chat_id} (modo: {mode})")
            
        except Exception as e:
            error_message = f"❌ Error obteniendo balance: {str(e)}"
            await bot.send_message(chat_id, error_message)
            logger.error(f"❌ Error en get_balance_async: {e}")

 