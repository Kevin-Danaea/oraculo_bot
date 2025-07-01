"""
Router para integración con el servicio Cerebro
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared.services.logging_config import get_logger
from services.grid.schedulers.multibot_scheduler import (
    get_multibot_scheduler
)
from services.grid.core.cerebro_integration import cerebro_client
from services.grid.core.trading_mode_manager import trading_mode_manager
from services.grid.data.config_repository import get_all_active_configs, get_all_active_configs_for_user
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/cerebro", tags=["Cerebro"])

class DecisionCerebro(BaseModel):
    """Modelo para recibir decisiones del Cerebro"""
    par: str
    decision: str  # OPERAR_GRID o PAUSAR_GRID
    adx_valor: float
    volatilidad_valor: float
    sentiment_promedio: float
    timestamp: str
    razon: str = ""  # Campo opcional para la razón
    fuente: str = "cerebro"  # Campo opcional para la fuente

@router.post("/decision")
async def recibir_decision_cerebro(decision: DecisionCerebro):
    """
    Endpoint para recibir decisiones automáticas del Cerebro
    IMPLEMENTACIÓN AUTÓNOMA: El Grid responde automáticamente a las decisiones
    """
    try:
        # Actualizar estado global
        cerebro_client.estado_cerebro.update({
            "decision": decision.decision,
            "ultima_actualizacion": decision.timestamp,
            "fuente": "cerebro_notificacion_automatica"
        })
        
        logger.info(f"🧠 Nueva decisión del Cerebro: {decision.decision}")
        logger.info(f"📊 Par: {decision.par} | ADX: {decision.adx_valor} | Volatilidad: {decision.volatilidad_valor} | Sentimiento: {decision.sentiment_promedio}")
        
        # LÓGICA AUTÓNOMA: Actuar según la decisión del cerebro
        scheduler = get_multibot_scheduler()
        bot_status = scheduler.get_status()
        
        if decision.decision == "OPERAR_GRID":
            # Verificar si el bot para este par ya está ejecutándose
            par_activo = any(bot['pair'] == decision.par for bot in bot_status['active_bots'])
            
            logger.info(f"🚀 Cerebro autoriza trading para {decision.par} - Estado actual: {'Activo' if par_activo else 'Inactivo'}")
            
            # NOTA: Ya no necesitamos cooldown porque el cerebro no envía duplicados
            # El problema de duplicados se resolvió en el origen
            should_send_notification = True
            
            if not par_activo:
                logger.info(f"🚀 Cerebro autoriza trading para {decision.par} - Iniciando bot...")
                
                # Obtener configuración del par desde la base de datos (todas las configuraciones)
                try:
                    configs = get_all_active_configs()
                    
                    # Buscar configuración para este par
                    config_par = None
                    for config in configs:
                        if config['pair'] == decision.par:
                            config_par = config
                            break
                    
                    if config_par:
                        # Iniciar bot específico para este par
                        success = scheduler.start_bot_for_pair(decision.par, config_par)
                        if success:
                            logger.info(f"✅ Bot para {decision.par} iniciado automáticamente")
                        else:
                            logger.error(f"❌ Error iniciando bot para {decision.par}")
                    else:
                        logger.warning(f"⚠️ No se encontró configuración para {decision.par}")
                        
                except Exception as e:
                    logger.error(f"❌ Error obteniendo configuración para {decision.par}: {e}")
            else:
                logger.info(f"ℹ️ Bot para {decision.par} ya está ejecutándose - Cerebro confirma continuar")
            
            # Enviar notificación solo si es necesario
            if should_send_notification:
                try:
                    from shared.services.telegram_service import send_telegram_message
                    
                    # Obtener configuración del par para mostrar detalles
                    configs = get_all_active_configs()
                    config_par = None
                    for config in configs:
                        if config['pair'] == decision.par:
                            config_par = config
                            break
                    
                    # Mensaje detallado de autorización
                    start_message = f"🚀 <b>GRID BOT AUTORIZADO</b>\n\n"
                    start_message += f"📊 Par: {decision.par}\n"
                    
                    if config_par:
                        start_message += f"💰 Capital: ${config_par['total_capital']:,.2f}\n"
                        start_message += f"🎯 Niveles: {config_par['grid_levels']}\n"
                        start_message += f"📈 Rango: {config_par['price_range_percent']}%\n"
                    
                    start_message += f"📈 ADX: {decision.adx_valor:.2f}\n"
                    start_message += f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                    start_message += f"💬 Sentimiento: {decision.sentiment_promedio:.3f}\n\n"
                    start_message += f"✅ <b>Razón de autorización:</b>\n"
                    start_message += f"• {decision.razon}\n\n"
                    start_message += f"🟢 El bot está operando automáticamente"
                    
                    send_telegram_message(start_message)
                    logger.info(f"✅ Notificación de autorización enviada para {decision.par}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
            else:
                logger.info(f"⏳ Notificación omitida para {decision.par} (cooldown activo)")
                
        elif decision.decision == "PAUSAR_GRID":
            # Verificar si el bot para este par está ejecutándose
            par_activo = any(bot['pair'] == decision.par for bot in bot_status['active_bots'])
            
            logger.info(f"🛑 Cerebro recomienda pausar {decision.par} - Estado actual: {'Activo' if par_activo else 'Inactivo'}")
            
            # Verificar si ya se envió una notificación reciente para este par
            from datetime import datetime
            current_time = datetime.now()
            last_notification_key = f"last_notification_{decision.par}"
            last_notification_time = getattr(recibir_decision_cerebro, last_notification_key, None)
            
            # Solo enviar notificación si han pasado más de 30 segundos desde la última
            should_send_notification = True
            if last_notification_time:
                time_diff = current_time - last_notification_time
                if time_diff.total_seconds() < 30:  # 30 segundos de cooldown
                    should_send_notification = False
                    logger.info(f"⏳ Notificación reciente para {decision.par} - saltando (cooldown 30s)")
            
            if par_activo:
                logger.info(f"🛑 Cerebro recomienda pausar {decision.par} - Deteniendo bot...")
                success = scheduler.stop_bot_for_pair(decision.par)
                if success:
                    logger.info(f"✅ Bot para {decision.par} detenido automáticamente")
                else:
                    logger.error(f"❌ Error deteniendo bot para {decision.par}")
            else:
                logger.info(f"ℹ️ Bot para {decision.par} ya está pausado - Cerebro confirma mantener pausado")
            
            # Enviar notificación solo si es necesario
            if should_send_notification:
                try:
                    from shared.services.telegram_service import send_telegram_message
                    
                    # Obtener configuración del par para mostrar detalles
                    configs = get_all_active_configs()
                    config_par = None
                    for config in configs:
                        if config['pair'] == decision.par:
                            config_par = config
                            break
                    
                    # Mensaje detallado de pausa
                    pause_message = f"⏸️ <b>GRID BOT PAUSADO</b>\n\n"
                    pause_message += f"📊 Par: {decision.par}\n"
                    
                    if config_par:
                        pause_message += f"💰 Capital: ${config_par['total_capital']:,.2f}\n"
                        pause_message += f"🎯 Niveles: {config_par['grid_levels']}\n"
                        pause_message += f"📈 Rango: {config_par['price_range_percent']}%\n"
                    
                    pause_message += f"📈 ADX: {decision.adx_valor:.2f}\n"
                    pause_message += f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                    pause_message += f"💬 Sentimiento: {decision.sentiment_promedio:.3f}\n\n"
                    pause_message += f"🛑 <b>Razón de pausa:</b>\n"
                    pause_message += f"• {decision.razon}\n\n"
                    pause_message += f"🔄 El bot se reactivará automáticamente cuando el Cerebro autorice"
                    
                    send_telegram_message(pause_message)
                    logger.info(f"✅ Notificación de pausa enviada para {decision.par}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
            else:
                logger.info(f"⏳ Notificación omitida para {decision.par} (cooldown activo)")
        
        return {
            "status": "success",
            "message": f"Decisión {decision.decision} procesada y ejecutada automáticamente",
            "action_taken": "start" if decision.decision == "OPERAR_GRID" and not par_activo else 
                           "stop" if decision.decision == "PAUSAR_GRID" and par_activo else "none",
            "timestamp": decision.timestamp
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando decisión del Cerebro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/estado")
def obtener_estado_cerebro():
    """
    Obtiene el estado actual de la decisión del Cerebro
    """
    config = trading_mode_manager.get_config()
    
    return {
        "estado_cerebro": cerebro_client.estado_cerebro,
        "modo_trading": config["modo"],
        "timestamp": cerebro_client.estado_cerebro.get("ultima_actualizacion"),
        "status": "active"
    }

@router.get("/batch/analysis")
async def get_batch_analysis():
    """
    Endpoint para obtener análisis batch del cerebro desde el Grid.
    Mejora la eficiencia al obtener todas las decisiones de una vez.
    
    Returns:
        Análisis completo de todos los pares desde el cerebro
    """
    try:
        logger.info("🚀 ========== SOLICITUD DE ANÁLISIS BATCH DESDE GRID ==========")
        
        # Consultar análisis batch del cerebro
        decisiones_batch = await cerebro_client.consultar_y_procesar_batch()
        
        if not decisiones_batch:
            raise HTTPException(
                status_code=500,
                detail="No se pudo obtener análisis batch del cerebro"
            )
        
        # Preparar respuesta
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_pairs": len(decisiones_batch),
            "pairs_analyzed": list(decisiones_batch.keys()),
            "decisions": decisiones_batch,
            "summary": {
                "OPERAR_GRID": 0,
                "PAUSAR_GRID": 0,
                "ERROR": 0
            }
        }
        
        # Calcular resumen
        for par, decision_data in decisiones_batch.items():
            if decision_data.get('success', False):
                decision = decision_data.get('decision', 'ERROR')
                response["summary"][decision] += 1
            else:
                response["summary"]["ERROR"] += 1
        
        logger.info(f"✅ Análisis batch completado desde Grid: {response['summary']}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en análisis batch desde Grid: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis batch: {str(e)}"
        ) 