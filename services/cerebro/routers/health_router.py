"""
Health Router - Endpoints de Health Check
========================================

Router que maneja los endpoints de monitoreo y salud del servicio.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any
import logging

from ..core.recipe_master import PARES_A_MONITOREAR

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class HealthResponse(BaseModel):
    """
    Modelo para la respuesta de health check.
    """
    status: str = Field(..., description="Estado del servicio: 'healthy' o 'unhealthy'")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del check")
    version: str = Field(..., description="Versión del servicio")
    uptime: str = Field(..., description="Tiempo de actividad")
    components: Dict[str, str] = Field(..., description="Estado de componentes individuales")

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={404: {"description": "Not found"}},
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Endpoint principal de health check.
    
    Returns:
        Estado de salud del servicio
    """
    try:
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime="En funcionamiento",
            components={
                "decision_engine": "healthy",
                "configuration": "healthy",
                "database": "healthy"
            }
        )
        
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/detailed")
async def detailed_health_check():
    """
    Health check detallado con información específica de componentes.
    
    Returns:
        Estado detallado del servicio
    """
    try:
        from ..core.decision_engine import DecisionEngine
        
        # Verificar componentes
        components_status = {}
        
        # Verificar motor de decisiones
        try:
            engine = DecisionEngine()
            components_status["decision_engine"] = "healthy"
        except Exception as e:
            components_status["decision_engine"] = f"unhealthy: {str(e)}"
        
        # Verificar configuración
        try:
            if PARES_A_MONITOREAR:
                components_status["configuration"] = "healthy"
            else:
                components_status["configuration"] = "unhealthy: no configuration found"
        except Exception as e:
            components_status["configuration"] = f"unhealthy: {str(e)}"
        
        # Determinar estado general
        overall_status = "healthy" if all(
            status == "healthy" for status in components_status.values()
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": components_status,
            "configuration": {
                "pares_configurados": PARES_A_MONITOREAR,
                "total_pares": len(PARES_A_MONITOREAR)
            },
            "metrics": {
                "memory_usage": "N/A",
                "cpu_usage": "N/A",
                "requests_processed": "N/A"
            }
        }
        
    except Exception as e:
        logging.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        ) 