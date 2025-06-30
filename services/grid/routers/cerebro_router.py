"""
Router para integración con el servicio Cerebro
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared.services.logging_config import get_logger
from services.grid.schedulers.grid_scheduler import (
    get_grid_bot_status, 
    start_grid_bot_manual, 
    stop_grid_bot_manual
)
from services.grid.core.cerebro_integration import (
    estado_cerebro,
    obtener_configuracion_trading
)

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

@router.post("/decision")
async def recibir_decision_cerebro(decision: DecisionCerebro):
    """
    Endpoint para recibir decisiones automáticas del Cerebro
    IMPLEMENTACIÓN AUTÓNOMA: El Grid responde automáticamente a las decisiones
    """
    try:
        # Actualizar estado global
        estado_cerebro.update({
            "decision": decision.decision,
            "ultima_actualizacion": decision.timestamp,
            "fuente": "cerebro_notificacion_automatica"
        })
        
        logger.info(f"🧠 Nueva decisión del Cerebro: {decision.decision}")
        logger.info(f"📊 Par: {decision.par} | ADX: {decision.adx_valor} | Volatilidad: {decision.volatilidad_valor} | Sentimiento: {decision.sentiment_promedio}")
        
        # LÓGICA AUTÓNOMA: Actuar según la decisión del cerebro
        bot_status = get_grid_bot_status()
        
        if decision.decision == "OPERAR_GRID":
            if not bot_status['bot_running']:
                logger.info("🚀 Cerebro autoriza trading - Iniciando Grid Bot automáticamente...")
                success, message = start_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot iniciado automáticamente por decisión del Cerebro")
                    # Enviar notificación por Telegram
                    try:
                        from shared.services.telegram_service import send_telegram_message
                        send_telegram_message(
                            f"🧠 <b>Grid iniciado automáticamente</b>\n\n"
                            f"✅ El Cerebro autorizó el trading\n"
                            f"📊 Par: {decision.par}\n"
                            f"📈 ADX: {decision.adx_valor:.2f}\n"
                            f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                            f"💬 Sentimiento: {decision.sentiment_promedio:.3f}\n"
                            f"⏰ {decision.timestamp}"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
                else:
                    logger.error(f"❌ Error iniciando Grid Bot automáticamente: {message}")
            else:
                logger.info("ℹ️ Grid Bot ya está ejecutándose - Cerebro confirma continuar")
                
        elif decision.decision == "PAUSAR_GRID":
            if bot_status['bot_running']:
                logger.info("🛑 Cerebro recomienda pausar - Deteniendo Grid Bot automáticamente...")
                success, message = stop_grid_bot_manual()
                if success:
                    logger.info("✅ Grid Bot detenido automáticamente por decisión del Cerebro")
                    # Enviar notificación por Telegram
                    try:
                        from shared.services.telegram_service import send_telegram_message
                        send_telegram_message(
                            f"🧠 <b>Grid pausado automáticamente</b>\n\n"
                            f"⚠️ El Cerebro recomendó pausar el trading\n"
                            f"📊 Par: {decision.par}\n"
                            f"📈 ADX: {decision.adx_valor:.2f}\n"
                            f"📊 Volatilidad: {decision.volatilidad_valor:.4f}\n"
                            f"💬 Sentimiento: {decision.sentiment_promedio:.3f}\n"
                            f"⏰ {decision.timestamp}\n\n"
                            f"🔄 El Grid se reactivará automáticamente cuando el Cerebro autorice"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo enviar notificación Telegram: {e}")
                else:
                    logger.error(f"❌ Error deteniendo Grid Bot automáticamente: {message}")
            else:
                logger.info("ℹ️ Grid Bot ya está pausado - Cerebro confirma mantener pausado")
        
        return {
            "status": "success",
            "message": f"Decisión {decision.decision} procesada y ejecutada automáticamente",
            "action_taken": "start" if decision.decision == "OPERAR_GRID" and not bot_status['bot_running'] else 
                           "stop" if decision.decision == "PAUSAR_GRID" and bot_status['bot_running'] else "none",
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
    config = obtener_configuracion_trading()
    
    return {
        "estado_cerebro": estado_cerebro,
        "modo_trading": config["modo"],
        "timestamp": estado_cerebro.get("ultima_actualizacion"),
        "status": "active"
    } 