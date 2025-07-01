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

from shared.services.logging_config import get_logger
from shared.database.session import get_db_session
from shared.database.models import GridBotConfig
from services.grid.core.trading_engine import run_grid_trading_bot
from services.grid.core.cerebro_integration import cerebro_client
from services.grid.data.config_repository import get_all_active_configs

logger = get_logger(__name__)

class MultibotScheduler:
    """
    Scheduler para manejar múltiples bots de grid simultáneamente.
    Cada par tiene su propio bot independiente.
    """
    
    def __init__(self):
        """Inicializa el scheduler multibot"""
        self.scheduler = BackgroundScheduler()
        self.bot_threads: Dict[str, threading.Thread] = {}
        self.bot_running: Dict[str, bool] = {}
        self.bot_configs: Dict[str, Dict[str, Any]] = {}
        
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
        Inicia un bot específico para un par
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            config: Configuración del bot
            
        Returns:
            True si se inició correctamente
        """
        try:
            if self.bot_running.get(pair, False):
                logger.warning(f"⚠️ Bot para {pair} ya está ejecutándose")
                return False
            
            logger.info(f"🚀 Iniciando bot para {pair}...")
            
            # Guardar configuración
            self.bot_configs[pair] = config
            
            # Crear y ejecutar hilo del bot
            bot_thread = threading.Thread(
                target=self._run_bot_for_pair,
                args=(pair, config),
                daemon=True,
                name=f"GridBot-{pair.replace('/', '-')}"
            )
            
            self.bot_threads[pair] = bot_thread
            self.bot_running[pair] = True
            
            bot_thread.start()
            
            # Actualizar estado en base de datos
            self._update_bot_status_in_db(pair, True, 'OPERAR_GRID')
            
            logger.info(f"✅ Bot para {pair} iniciado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando bot para {pair}: {e}")
            return False
    
    def stop_bot_for_pair(self, pair: str) -> bool:
        """
        Detiene un bot específico para un par
        
        Args:
            pair: Par de trading
            
        Returns:
            True si se detuvo correctamente
        """
        try:
            if not self.bot_running.get(pair, False):
                logger.warning(f"⚠️ Bot para {pair} no está ejecutándose")
                return False
            
            logger.info(f"🛑 Deteniendo bot para {pair}...")
            
            # Señalar detención
            self.bot_running[pair] = False
            
            # Esperar a que termine el hilo
            if pair in self.bot_threads:
                thread = self.bot_threads[pair]
                if thread.is_alive():
                    thread.join(timeout=30)
                    if thread.is_alive():
                        logger.warning(f"⚠️ Bot para {pair} no terminó en el tiempo esperado")
                        return False
            
            # Limpiar referencias
            self.bot_threads.pop(pair, None)
            self.bot_configs.pop(pair, None)
            
            # Actualizar estado en base de datos
            self._update_bot_status_in_db(pair, False, 'PAUSAR_GRID')
            
            logger.info(f"✅ Bot para {pair} detenido correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot para {pair}: {e}")
            return False
    
    def stop_all_bots(self):
        """Detiene todos los bots activos"""
        try:
            active_pairs = list(self.bot_running.keys())
            logger.info(f"🛑 Deteniendo {len(active_pairs)} bots activos...")
            
            for pair in active_pairs:
                self.stop_bot_for_pair(pair)
            
            logger.info("✅ Todos los bots detenidos")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo todos los bots: {e}")
    
    def _run_bot_for_pair(self, pair: str, config: Dict[str, Any]):
        """
        Ejecuta el bot para un par específico
        
        Args:
            pair: Par de trading
            config: Configuración del bot
        """
        try:
            logger.info(f"🤖 Ejecutando bot para {pair} con configuración: {config}")
            
            # Ejecutar el grid trading bot
            run_grid_trading_bot(config)
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando bot para {pair}: {e}")
        finally:
            self.bot_running[pair] = False
            logger.info(f"🛑 Bot para {pair} terminado")
    
    def _check_all_bots_health(self):
        """Verifica la salud de todos los bots activos"""
        try:
            active_pairs = list(self.bot_running.keys())
            
            for pair in active_pairs:
                if not self.bot_running.get(pair, False):
                    continue
                
                thread = self.bot_threads.get(pair)
                if not thread or not thread.is_alive():
                    logger.warning(f"⚠️ Bot para {pair} se detuvo inesperadamente")
                    # Reiniciar bot si es necesario
                    self._restart_bot_if_needed(pair)
                else:
                    logger.debug(f"✅ Bot para {pair} ejecutándose correctamente")
                    
        except Exception as e:
            logger.error(f"❌ Error verificando salud de bots: {e}")
    
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
            is_running = config.get('is_running', False)
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
        """Reinicia un bot si es necesario"""
        try:
            # Verificar si debe estar ejecutándose según la base de datos
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active == True
                ).first()
                
                if config and getattr(config, 'last_decision', 'NO_DECISION') == 'OPERAR_GRID':
                    logger.info(f"🔄 Reiniciando bot para {pair}...")
                    config_dict = config.to_dict()
                    self.start_bot_for_pair(pair, config_dict)
                    
        except Exception as e:
            logger.error(f"❌ Error reiniciando bot para {pair}: {e}")
    
    def _update_bot_status_in_db(self, pair: str, is_running: bool, decision: str):
        """Actualiza el estado del bot en la base de datos"""
        try:
            with get_db_session() as db:
                config = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active == True
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
            from shared.services.telegram_service import send_telegram_message
            
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
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado completo del sistema multibot"""
        try:
            active_bots = []
            for pair, is_running in self.bot_running.items():
                if is_running:
                    thread = self.bot_threads.get(pair)
                    active_bots.append({
                        'pair': pair,
                        'running': True,
                        'thread_alive': thread.is_alive() if thread else False,
                        'config': self.bot_configs.get(pair, {})
                    })
            
            return {
                'scheduler_running': self.scheduler.running,
                'active_bots': active_bots,
                'total_active_bots': len(active_bots),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado multibot: {e}")
            return {
                'scheduler_running': False,
                'active_bots': [],
                'total_active_bots': 0,
                'error': str(e),
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