"""
Multibot Scheduler - Maneja múltiples bots de grid simultáneamente
Cada par (ETH, BTC, AVAX) tiene su propio bot independiente que se ejecuta en paralelo.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
import html

from shared.services.logging_config import get_logger
from shared.database.session import get_db_session
from shared.database.models import GridBotConfig, EstrategiaStatus
from services.grid.core.trading_engine import run_grid_trading_bot
from services.grid.core.cerebro_integration import cerebro_client
from services.grid.data.config_repository import get_all_active_configs
from services.grid.core.trade_aggregator import trade_aggregator
from services.grid.core.config_manager import get_exchange_connection
from shared.services.telegram_service import send_telegram_message

logger = get_logger(__name__)

class MultibotScheduler:
    """
    Scheduler para manejar múltiples bots de grid simultáneamente.
    Cada par tiene su propio bot independiente.
    """
    
    def __init__(self):
        """Inicializa el scheduler multibot."""
        self.scheduler = BackgroundScheduler(daemon=True)
        self.active_bots: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.last_cerebro_check = None
        self.cerebro_check_job = None
        self.trade_summary_job = None
        
        # Configurar scheduler
        self._setup_scheduler()
        
    def _setup_scheduler(self):
        """Configura los jobs del scheduler"""
        try:
            # Verificación de salud de todos los bots cada 5 minutos
            self.scheduler.add_job(
                func=self._check_all_bots_health,
                trigger=IntervalTrigger(minutes=5),
                id='multibot_health_check',
                name='Multibot Health Check',
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=60
            )
            
            # Monitoreo de decisiones del cerebro cada 1 hora (sincronizado con cerebro)
            self.scheduler.add_job(
                func=self.check_cerebro_decisions,
                trigger=IntervalTrigger(hours=1),
                id='cerebro_decisions_check',
                name='Cerebro Decisions Check',
                replace_existing=True
            )
            
            # Tarea para enviar resumen de actividad cada 30 minutos
            self.scheduler.add_job(
                func=self.send_periodic_trade_summary,
                trigger=IntervalTrigger(minutes=30),
                id='periodic_trade_summary',
                name='Periodic Trade Summary',
                replace_existing=True
            )
            
            logger.info("✅ Multibot Scheduler configurado correctamente")
            logger.info("🔄 Verificación de salud programada cada 5 minutos")
            logger.info("🧠 Monitoreo del cerebro programado cada 1 hora")
            
        except Exception as e:
            logger.error(f"❌ Error configurando Multibot Scheduler: {e}")
            raise
    
    def start(self):
        """Inicia el scheduler multibot"""
        try:
            if self.scheduler.running:
                logger.info("✅ Multibot Scheduler ya está ejecutándose")
                return
            
            self.scheduler.start()
            logger.info("✅ Multibot Scheduler iniciado")
            logger.info("🤖 Sistema multibot en MODO AUTÓNOMO")
            logger.info("📊 Múltiples bots pueden ejecutarse simultáneamente")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Multibot Scheduler: {e}")
            raise
    
    def stop(self):
        """Detiene el scheduler y todos los bots"""
        try:
            # Detener todos los bots
            self.stop_all_bots()
            
            # Detener scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Multibot Scheduler detenido")
                
        except Exception as e:
            logger.error(f"❌ Error deteniendo Multibot Scheduler: {e}")
    
    def start_bot_for_pair(self, pair: str, config: Dict[str, Any]) -> bool:
        """
        Inicia un bot específico para un par en un hilo separado.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            config: Configuración del bot
            
        Returns:
            True si se inició correctamente
        """
        with self.lock:
            if pair in self.active_bots:
                logger.warning(f"⚠️ Bot para {pair} ya está ejecutándose")
                return False
            
            logger.info(f"🚀 Iniciando bot para {pair}...")
            
            bot_thread = threading.Thread(
                target=self._run_bot_for_pair,
                args=(pair, config),
                daemon=True,
                name=f"GridBot-{pair.replace('/', '-')}"
            )
            
            self.active_bots[pair] = {
                'thread': bot_thread,
                'config': config,
                'status': 'running'  # Estado: 'running' o 'stopping'
            }
            
            bot_thread.start()
            
            # Actualizar estado en base de datos
            self._update_bot_status_in_db(pair, True, 'OPERAR_GRID')
            
            logger.info(f"✅ Bot para {pair} iniciado correctamente")
            return True
    
    def stop_bot_for_pair(self, pair: str) -> bool:
        """
        Señala a un bot específico que debe detenerse.
        
        Args:
            pair: Par de trading
            
        Returns:
            True si la señal se envió correctamente
        """
        with self.lock:
            if pair not in self.active_bots:
                logger.warning(f"⚠️ Bot para {pair} no está ejecutándose")
                return False
            
            logger.info(f"🛑 Señalando parada para bot {pair}...")
            
            # Señalar detención. El hilo del bot se encargará de la limpieza.
            self.active_bots[pair]['status'] = 'stopping'
            
            # NO esperamos (join) aquí para no bloquear el hilo principal.
            # El hilo del bot se auto-limpiará de la lista de `active_bots`.
            return True
    
    def stop_all_bots(self):
        """
        Señala a todos los bots en ejecución que deben detenerse.
        """
        with self.lock:
            if not self.active_bots:
                logger.info("ℹ️ No hay bots activos para detener")
                return
            
            logger.info(f"🛑 Señalando parada para {len(self.active_bots)} bots...")
            pairs_to_stop = list(self.active_bots.keys())
            
            for pair in pairs_to_stop:
                if pair in self.active_bots:
                    self.active_bots[pair]['status'] = 'stopping'

    def force_stop_and_clear_all(self):
        """
        Forzosamente detiene todos los bots y limpia el estado interno.
        Esto es para reinicios y cambios de modo, no para una parada normal.
        """
        with self.lock:
            if not self.active_bots:
                return

            pairs_to_stop = list(self.active_bots.keys())
            logger.warning(f"🚨 Forzando parada y limpieza de {len(pairs_to_stop)} bots.")
            
            # Señal para que el hilo muera en su próximo ciclo de verificación
            for pair in pairs_to_stop:
                if pair in self.active_bots:
                    self.active_bots[pair]['status'] = 'stopping' 
            
            # Limpiar el diccionario para permitir que los nuevos bots se inicien inmediatamente
            self.active_bots.clear()
            logger.info("✅ Diccionario de bots activos del scheduler limpiado forzosamente.")

    def _run_bot_for_pair(self, pair: str, config: Dict[str, Any]):
        """
        Wrapper que se ejecuta en un hilo para manejar el ciclo de vida de un bot.
        
        Args:
            pair: Par de trading
            config: Configuración del bot
        """
        try:
            logger.info(f"🤖 Ejecutando bot para {pair} con configuración: {config}")
            run_grid_trading_bot(config)
        except Exception as e:
            logger.error(f"❌ Error fatal en hilo del bot para {pair}: {e}")
        finally:
            logger.info(f"🛑 Hilo del bot para {pair} terminado")
            with self.lock:
                # Limpiar el bot de la lista de activos
                if pair in self.active_bots:
                    self.active_bots.pop(pair, None)
            
            # Actualizar estado en la base de datos a 'no ejecutándose'
            self._update_bot_status_in_db(pair, False, 'PAUSAR_GRID')
    
    def _check_all_bots_health(self):
        """Verifica la salud de todos los bots activos y reinicia si es necesario."""
        with self.lock:
            dead_bots_pairs = []
            active_pairs = list(self.active_bots.keys())
            
            for pair in active_pairs:
                bot_data = self.active_bots.get(pair)
                if not bot_data or not bot_data['thread'].is_alive():
                    logger.warning(f"⚠️ Bot para {pair} se detuvo inesperadamente (hilo muerto).")
                    dead_bots_pairs.append(pair)
            
            # Sacar del lock para llamar a la función de reinicio
            if dead_bots_pairs:
                logger.info(f"Encontrados {len(dead_bots_pairs)} bots muertos para procesar.")

        # Fuera del lock para evitar deadlocks
        for pair in dead_bots_pairs:
            with self.lock:
                self.active_bots.pop(pair, None)  # Asegurar que se elimina
            logger.info(f"Bot muerto {pair} eliminado de la lista activa.")
            self._restart_bot_if_needed(pair)
                    
    def check_cerebro_decisions(self):
        """
        Verifica las decisiones del cerebro para todos los pares configurados.
        NUEVA LÓGICA BATCH: Usa análisis batch del cerebro para mayor eficiencia.
        SINCRONIZADO: Consulta cada 1 hora (mismo intervalo que el cerebro).
        """
        try:
            logger.info("🧠 ========== VERIFICANDO DECISIONES DEL CEREBRO (BATCH) ==========")
            
            # Obtener TODAS las configuraciones activas de TODOS los usuarios
            configuraciones = get_all_active_configs()
            
            if not configuraciones:
                logger.warning("⚠️ No hay configuraciones activas para verificar")
                return
            
            logger.info(f"📊 Configuraciones a verificar: {len(configuraciones)}")
            
            # CONSULTA BATCH: Obtener todas las decisiones de una vez
            decisiones_batch = asyncio.run(cerebro_client.consultar_y_procesar_batch())
            
            if not decisiones_batch:
                logger.warning("⚠️ No se pudieron obtener decisiones batch del cerebro")
                logger.info("🔄 Reintentando con consultas individuales...")
                asyncio.run(self._check_cerebro_decisions_individual(configuraciones))
                return
            
            logger.info(f"✅ Decisiones batch obtenidas: {len(decisiones_batch)} pares")
            
            # Procesar cada configuración con las decisiones batch
            cambios_aplicados = 0
            
            for config in configuraciones:
                try:
                    par = config['pair']
                    
                    if par not in decisiones_batch:
                        logger.warning(f"⚠️ No se encontró decisión batch para {par}")
                        continue
                    
                    decision_data = decisiones_batch[par]
                    
                    if not decision_data.get('success', False):
                        logger.error(f"❌ Error en decisión batch para {par}: {decision_data.get('razon', 'Error desconocido')}")
                        continue
                    
                    decision = decision_data['decision']
                    razon = decision_data['razon']
                    indicadores = decision_data.get('indicadores', {})
                    
                    logger.info(f"📊 {par}: {decision} - {razon}")
                    logger.info(f"   ADX: {indicadores.get('adx_actual', 'N/A'):.2f}, Volatilidad: {indicadores.get('volatilidad_actual', 'N/A'):.4f}")
                    
                    # Aplicar decisión del cerebro
                    cambio_aplicado = self._aplicar_decision_cerebro(config, decision, razon, indicadores)
                    if cambio_aplicado:
                        cambios_aplicados += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando configuración {config.get('pair', 'N/A')}: {e}")
                    continue
            
            # Enviar resumen único por Telegram
            self._enviar_resumen_cerebro(cambios_aplicados, len(configuraciones))
            
            logger.info(f"✅ ========== VERIFICACIÓN BATCH DEL CEREBRO COMPLETADA ==========")
            logger.info(f"📈 Cambios aplicados: {cambios_aplicados}/{len(configuraciones)} configuraciones")
            
        except Exception as e:
            logger.error(f"❌ Error en verificación batch del cerebro: {e}")
            logger.info("🔄 Reintentando con consultas individuales...")
            # La variable 'configuraciones' ya fue definida en el bloque 'try'.
            # Podemos usarla directamente para el fallback a consultas individuales.
            asyncio.run(self._check_cerebro_decisions_individual(configuraciones))
    
    async def _check_cerebro_decisions_individual(self, configuraciones):
        """
        Método de respaldo que usa consultas individuales si el batch falla.
        """
        try:
            logger.info("🔄 ========== VERIFICANDO DECISIONES DEL CEREBRO (INDIVIDUAL) ==========")
            
            for config in configuraciones:
                try:
                    par = config['pair']
                    
                    # Consultar decisión individual
                    resultado = await cerebro_client.consultar_estado_inicial(par)
                    
                    if resultado and resultado.get('par') == par:
                        decision = resultado.get('decision', 'ERROR')
                        razon = resultado.get('razon', 'Sin razón')
                        
                        logger.info(f"📊 {par}: {decision} - {razon}")
                        
                        # Aplicar decisión del cerebro
                        self._aplicar_decision_cerebro(config, decision, razon, {})
                        
                except Exception as e:
                    logger.error(f"❌ Error consultando {config.get('pair', 'N/A')}: {e}")
                    continue
            
            logger.info("✅ ========== VERIFICACIÓN INDIVIDUAL DEL CEREBRO COMPLETADA ==========")
            
        except Exception as e:
            logger.error(f"❌ Error en verificación individual del cerebro: {e}")
    
    def _aplicar_decision_cerebro(self, config, decision, razon, indicadores):
        """
        Aplica la decisión del cerebro a una configuración específica.
        
        Args:
            config: Configuración del bot
            decision: Decisión del cerebro (OPERAR_GRID/PAUSAR_GRID)
            razon: Razón de la decisión
            indicadores: Indicadores utilizados
            
        Returns:
            bool: True si se aplicó un cambio, False si no hubo cambios
        """
        try:
            par = config['pair']
            with self.lock:
                is_running = par in self.active_bots
            cambio_aplicado = False
            
            if decision == "OPERAR_GRID":
                if not is_running:
                    logger.info(f"🚀 Cerebro autoriza trading para {par} - Iniciando bot...")
                    self.start_bot_for_pair(par, config)
                    cambio_aplicado = True
                else:
                    logger.info(f"🟢 Bot para {par} ya está ejecutándose - Cerebro confirma continuar")
                    
            elif decision == "PAUSAR_GRID":
                if is_running:
                    logger.info(f"🛑 Cerebro ordena pausar trading para {par} - Deteniendo bot...")
                    self.stop_bot_for_pair(par)
                    cambio_aplicado = True
                else:
                    logger.info(f"ℹ️ Bot para {par} ya está pausado - Cerebro confirma mantener pausado")
                    
            else:
                logger.warning(f"⚠️ Decisión desconocida para {par}: {decision}")
                
            return cambio_aplicado
                
        except Exception as e:
            logger.error(f"❌ Error aplicando decisión del cerebro para {config.get('pair', 'N/A')}: {e}")
            return False
    
    def _restart_bot_if_needed(self, pair: str):
        """Reinicia un bot si se detuvo pero debería estar corriendo."""
        try:
            logger.info(f"🔄 Verificando si el bot para {pair} debe ser reiniciado...")
            with get_db_session() as db:
                config_db = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active
                ).first()
                
                # Verificar que existe una estrategia GRID para este par
                estrategia_status = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == pair,
                    EstrategiaStatus.estrategia == "GRID"
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                
                if not estrategia_status:
                    logger.warning(f"⚠️ No se encontró estrategia GRID para {pair} en estrategia_status")
                    return False
                
                if config_db and config_db.last_decision == 'OPERAR_GRID': # type: ignore
                    logger.info(f"✅ Decisión es OPERAR_GRID. Reiniciando bot para {pair}...")
                    
                    config_dict = {c.key: getattr(config_db, c.key) for c in config_db.__table__.columns}
                    self.start_bot_for_pair(pair, config_dict)
                else:
                    logger.info(f"ℹ️ No es necesario reiniciar el bot para {pair}. Decisión actual: {config_db.last_decision if config_db else 'N/A'}")
                    
        except Exception as e:
            logger.error(f"❌ Error reiniciando bot para {pair}: {e}")
    
    def _update_bot_status_in_db(self, pair: str, is_running: bool, decision: str):
        """Actualiza el estado del bot en la base de datos"""
        try:
            with get_db_session() as db:
                # Verificar que existe una estrategia GRID para este par
                estrategia_status = db.query(EstrategiaStatus).filter(
                    EstrategiaStatus.par == pair,
                    EstrategiaStatus.estrategia == "GRID"
                ).order_by(EstrategiaStatus.timestamp.desc()).first()
                
                if not estrategia_status:
                    logger.warning(f"⚠️ No se encontró estrategia GRID para {pair} en estrategia_status")
                    return
                
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active
                ).first()
                
                if config:
                    setattr(config, 'is_running', is_running)
                    setattr(config, 'last_decision', decision)
                    setattr(config, 'last_decision_timestamp', datetime.utcnow())
                    db.commit()
                    
        except Exception as e:
            logger.error(f"❌ Error actualizando estado en BD para {pair}: {e}")
    
    def _enviar_resumen_cerebro(self, cambios_aplicados: int, total_configuraciones: int):
        """
        Envía un resumen único de las decisiones del cerebro por Telegram.
        Evita mensajes duplicados enviando solo un resumen consolidado.
        
        Args:
            cambios_aplicados: Número de cambios aplicados
            total_configuraciones: Total de configuraciones verificadas
        """
        try:
            # Solo enviar resumen si hay cambios o es la primera verificación
            if cambios_aplicados > 0:
                message = f"🧠 <b>RESUMEN CEREBRO - DECISIONES APLICADAS</b>\n\n"
                message += f"✅ <b>Cambios aplicados:</b> {cambios_aplicados}/{total_configuraciones}\n"
                message += f"📊 <b>Configuraciones verificadas:</b> {total_configuraciones}\n\n"
                
                if cambios_aplicados == total_configuraciones:
                    message += f"🟢 <b>Todos los bots actualizados según el cerebro</b>\n"
                elif cambios_aplicados > 0:
                    message += f"🔄 <b>Algunos bots actualizados según el cerebro</b>\n"
                
                message += f"\n⏰ <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
                
                send_telegram_message(message)
                logger.info(f"✅ Resumen del cerebro enviado: {cambios_aplicados} cambios")
            else:
                logger.info("ℹ️ No hay cambios que reportar del cerebro")
                
        except Exception as e:
            logger.error(f"❌ Error enviando resumen del cerebro: {e}")
    
    def send_periodic_trade_summary(self):
        """
        Envía un resumen periódico de toda la actividad de trading.
        Se ejecuta cada 30 minutos y consolida todos los movimientos.
        """
        summary = trade_aggregator.get_and_clear_summary()
        if not any(trades['buys'] or trades['sells'] for trades in summary.values()):
            logger.info("ℹ️ No hay trades en este período para resumir.")
            return

        try:
            message = "🕒 <b>GRID BOT - RESUMEN DE ACTIVIDAD</b> 🕒\n\n"
            total_realized_pnl = 0.0

            for pair, trades in summary.items():
                buys = trades.get('buys', [])
                sells = trades.get('sells', [])

                if not buys and not sells:
                    continue

                message += f"--- <b>{pair}</b> ---\n"
                message += f"📈 <b>Trades:</b> {len(buys)} compras, {len(sells)} ventas\n"

                buy_volume = sum(b.get('quantity', 0) * b.get('price', 0) for b in buys)
                sell_volume = sum(s.get('quantity', 0) * s.get('price', 0) for s in sells)

                message += f"💰 <b>Vol. Comprado:</b> ${buy_volume:.2f}\n"
                message += f"💰 <b>Vol. Vendido:</b> ${sell_volume:.2f}\n"

                pair_pnl = 0.0
                sell_details = ""
                for trade in sells:
                    buy_price = trade.get('buy_price')
                    if buy_price:
                        pnl = (trade.get('price', 0) - buy_price) * trade.get('quantity', 0)
                        pair_pnl += pnl
                        sell_details += f"  - Venta de {trade.get('quantity', 0):.4f} a ${trade.get('price', 0):.2f} (Ganancia: ${pnl:.2f})\n"
                
                total_realized_pnl += pair_pnl
                message += f"✅ <b>Ganancia Realizada:</b> ${pair_pnl:.2f}\n"
                if sell_details:
                    message += f"   <b>Detalle de Ventas:</b>\n{sell_details}"
                message += "\n"

            message += "--- <b>RESUMEN GENERAL</b> ---\n"
            exchange = get_exchange_connection()
            
            # CORRECCIÓN P&L: Usar solo bots activos para el cálculo
            status = self.get_status()
            active_bots_configs = [bot['config'] for bot in status['active_bots']]
            total_initial_capital = sum(c.get('total_capital', 0) for c in active_bots_configs)

            balance = exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # El valor total ahora se calcula basado en los activos de los bots que están corriendo
            total_value = usdt_balance
            message += "🏦 <b>Balance de Cuenta (Activos Relevantes):</b>\n"
            message += f"  • 💵 USDT: ${usdt_balance:.2f}\n"

            icon_map = {'ETH': '💎', 'BTC': '🟠', 'AVAX': '🔴'}
            # Iterar solo sobre los bots activos
            for config in active_bots_configs:
                pair = config['pair']
                crypto_symbol = pair.split('/')[0]
                crypto_balance = balance.get(crypto_symbol, {}).get('total', 0)
                if crypto_balance > 1e-5:
                    current_price = exchange.fetch_ticker(pair)['last']
                    crypto_value = crypto_balance * current_price
                    total_value += crypto_value
                    icon = icon_map.get(crypto_symbol, '🪙')
                    message += f"  • {icon} {crypto_symbol}: {crypto_balance:.6f} (${crypto_value:.2f})\n"
            
            message += f"  • <b>Total Estimado (Activos en Juego):</b> ${total_value:.2f}\n\n"

            if total_initial_capital > 0:
                pnl_vs_initial = total_value - total_initial_capital
                pnl_percentage = (pnl_vs_initial / total_initial_capital) * 100
                pnl_icon = "💹" if pnl_vs_initial >= 0 else "🔻"
                message += f"{pnl_icon} <b>P&L vs Capital Inicial (Activo):</b> ${pnl_vs_initial:.2f} ({pnl_percentage:.2f}%)\n"
                message += f"   <i>(Capital Inicial Activo: ${total_initial_capital:.2f})</i>\n\n"
            
            message += f"✅ <b>Ganancia Realizada (este período):</b> ${total_realized_pnl:.2f}\n"
            message += f"\n🕐 <i>{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            send_telegram_message(message)
            logger.info("✅ Resumen periódico de trades enviado correctamente.")

        except Exception as e:
            logger.error(f"❌ Error enviando resumen periódico de trades: {e}")
    
    def _enviar_resumen_cerebro_detallado(
        self, 
        bots_iniciados: List[Dict[str, Any]], 
        bots_pausados: List[Dict[str, Any]], 
        total_configuraciones: int
    ):
        """
        Envía un resumen detallado de los cambios aplicados por el Cerebro.
        """
        try:
            
            message = "🧠 <b>RESUMEN PERIÓDICO - CEREBRO</b>\n\n"
            message += "El sistema ha aplicado automáticamente las siguientes decisiones:\n\n"

            if bots_iniciados:
                message += "🚀 <b>Bots Iniciados:</b>\n"
                for bot in bots_iniciados:
                    message += f"  • <b>{bot['par']}</b>: {html.escape(bot['razon'])}\n"
                message += "\n"

            if bots_pausados:
                message += "⏸️ <b>Bots Pausados:</b>\n"
                for bot in bots_pausados:
                    message += f"  • <b>{bot['par']}</b>: {html.escape(bot['razon'])}\n"
                message += "\n"
            
            status = self.get_status()
            message += f"📊 <b>Estado Actual:</b> {status['total_active_bots']} de {total_configuraciones} bots ejecutándose.\n"
            message += f"⏰ Próximo análisis en ~1 hora."
            
            send_telegram_message(message)
            logger.info("✅ Resumen de decisiones del Cerebro enviado a Telegram")
            
        except ImportError:
            logger.error("❌ No se pudo enviar resumen del cerebro (error de importación)")
        except Exception as e:
            logger.error(f"❌ Error enviando resumen del Cerebro: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado completo del sistema multibot de forma thread-safe."""
        with self.lock:
            active_bots_info = []
            
            # Crear una copia para evitar errores de concurrencia al iterar
            active_bots_copy = list(self.active_bots.items())
            
            for pair, data in active_bots_copy:
                thread = data.get('thread')
                active_bots_info.append({
                    'pair': pair,
                    'running': data.get('status') == 'running',
                    'thread_alive': thread.is_alive() if thread else False,
                    'config': data.get('config', {})
                })
            
            # La lista de pares activos que el monitor necesita
            active_pairs = [pair for pair, data in active_bots_copy if data.get('status') == 'running']

            return {
                'scheduler_running': self.scheduler.running,
                'active_bots': active_bots_info,
                'total_active_bots': len(active_bots_info),
                'active_pairs': active_pairs,  # Para que `check_manual_stop_requested` funcione
                'timestamp': datetime.now().isoformat()
            }


# Instancia global del scheduler multibot
_multibot_scheduler: Optional[MultibotScheduler] = None

def get_multibot_scheduler() -> MultibotScheduler:
    """Obtiene la instancia global del scheduler multibot"""
    global _multibot_scheduler
    if _multibot_scheduler is None:
        _multibot_scheduler = MultibotScheduler()
    return _multibot_scheduler

def start_multibot_scheduler():
    """
    Función de conveniencia para iniciar el scheduler multibot.
    
    Returns:
        True si se inició correctamente o ya estaba corriendo
    """
    try:
        scheduler = get_multibot_scheduler()
        
        if scheduler.scheduler.running:
            logger.info("✅ Multibot Scheduler ya está ejecutándose")
            return True
        
        scheduler.start()
        logger.info("✅ Multibot Scheduler iniciado")
        return True
    except Exception as e:
        logger.error(f"❌ Error iniciando multibot scheduler: {e}")
        return False

def stop_multibot_scheduler():
    """
    Función de conveniencia para detener el scheduler multibot.
    
    Returns:
        True si se detuvo correctamente
    """
    try:
        scheduler = get_multibot_scheduler()
        scheduler.stop()
        logger.info("✅ Multibot Scheduler detenido")
        return True
    except Exception as e:
        logger.error(f"❌ Error deteniendo multibot scheduler: {e}")
        return False

__all__ = [
    'MultibotScheduler',
    'get_multibot_scheduler',
    'start_multibot_scheduler',
    'stop_multibot_scheduler'
] 