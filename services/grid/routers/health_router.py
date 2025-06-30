"""
Router para health checks del servicio Grid
"""

from datetime import datetime
from fastapi import APIRouter
from services.grid.schedulers.grid_scheduler import get_grid_scheduler

router = APIRouter(tags=["Health"])

@router.get("/")
def read_root():
    """Endpoint básico para verificar que el Grid Worker está vivo."""
    return {
        "worker": "grid",
        "status": "alive",
        "description": "Worker de trading - Grid trading automatizado en Binance"
    }

@router.get("/health")
async def health_check():
    """
    Endpoint de health check para el Grid Worker.
    """
    try:
        # Verificar que el scheduler esté activo
        scheduler = get_grid_scheduler()
        if scheduler and scheduler.running:
            return {
                "status": "healthy",
                "service": "Grid Trading Service",
                "version": "3.0.0",
                "scheduler": "running",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "service": "Grid Trading Service", 
                "version": "3.0.0",
                "scheduler": "stopped",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "Grid Trading Service",
            "version": "3.0.0", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 