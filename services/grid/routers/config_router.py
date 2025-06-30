"""
Router para configuración del servicio Grid
"""

from fastapi import APIRouter, HTTPException
from shared.services.logging_config import get_logger
from services.grid.core.cerebro_integration import alternar_modo_trading

logger = get_logger(__name__)
router = APIRouter(prefix="/modo", tags=["Configuración"])

@router.post("/alternar")
def alternar_modo_trading_endpoint():
    """
    Alterna entre modo productivo y sandbox
    """
    try:
        config = alternar_modo_trading()
        
        return {
            "status": "success",
            "nuevo_modo": config["modo"],
            "descripcion": config["descripcion"],
            "message": f"Modo cambiado a {config['modo']}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error alternando modo: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 