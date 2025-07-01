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
    Endpoint para recibir decisiones automáticas del Cerebro.
    SOLO REGISTRA LA DECISIÓN. El scheduler la aplicará en su ciclo.
    """
    try:
        # Actualizar estado global para monitoreo por /status
        cerebro_client.estado_cerebro.update({
            "decision": decision.decision,
            "ultima_actualizacion": decision.timestamp,
            "fuente": "cerebro_notificacion_automatica"
        })
        
        logger.info(f"🧠 Decisión del Cerebro RECIBIDA y REGISTRADA: {decision.decision} para {decision.par}")
        logger.info(f"   - Razón: {decision.razon}")
        logger.info(f"   - El scheduler la aplicará en el próximo ciclo de verificación.")

        # La decisión ya fue guardada en la BD por el servicio Cerebro.
        # Este endpoint solo acusa recibo. No ejecuta ninguna acción para
        # evitar condiciones de carrera con el inicio/parada manual.
        # El scheduler, en su ciclo, se encargará de aplicar los cambios.
        
        return {
            "status": "success",
            "message": f"Decisión '{decision.decision}' para {decision.par} registrada. El scheduler actuará en su próximo ciclo.",
            "action_taken": "none",
            "timestamp": decision.timestamp
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando recepción de decisión del Cerebro: {e}")
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