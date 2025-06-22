"""
Router de Grid Trading - Endpoints del bot de trading automatizado
Proporciona control y monitoreo del grid trading bot.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from shared.services.logging_config import get_logger
from services.grid.schedulers.grid_scheduler import get_grid_scheduler, get_grid_bot_config
from services.grid.core.trading_engine import force_reset_bot

logger = get_logger(__name__)

# Crear el router
router = APIRouter()

# --- Endpoints de Grid Trading ---
@router.get("/", tags=["Grid Trading"])
def grid_status():
    """Estado general del servicio de grid trading."""
    try:
        scheduler = get_grid_scheduler()
        is_running = scheduler.running if scheduler else False
        
        return {
            "service": "grid",
            "status": "operational" if is_running else "stopped",
            "scheduler_running": is_running,
            "endpoints": {
                "status": "/status",
                "config": "/config",
                "reset": "/reset"
            }
        }
    except Exception as e:
        return {
            "service": "grid",
            "status": "error",
            "error": str(e)
        }

@router.get("/status", tags=["Grid Trading"])
def grid_detailed_status():
    """
    Estado detallado del grid trading bot incluyendo scheduler y jobs.
    """
    try:
        scheduler = get_grid_scheduler()
        
        if not scheduler or not scheduler.running:
            return {
                "service": "grid",
                "status": "scheduler_stopped",
                "message": "El scheduler del grid bot no está ejecutándose",
                "jobs": []
            }
        
        jobs_info = []
        for job in scheduler.get_jobs():
            job_data = {
                "id": job.id,
                "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            jobs_info.append(job_data)
        
        return {
            "service": "grid",
            "status": "running",
            "message": f"Grid Bot activo con {len(jobs_info)} tareas programadas",
            "jobs": jobs_info,
            "features": [
                "🤖 Bot de Grid Trading automatizado",
                "💹 Trading en Binance con estrategia de grilla",
                "🔄 Monitoreo continuo cada 30 segundos",
                "💰 Ganancia objetivo del 1% por trade",
                "📊 Reportes automáticos por Telegram"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener estado del grid bot: {e}")
        return {
            "service": "grid",
            "status": "error",
            "message": f"Error al obtener el estado: {str(e)}"
        }

@router.get("/config", tags=["Grid Trading"])
def get_grid_config():
    """
    Obtiene la configuración actual del grid trading bot.
    """
    try:
        config = get_grid_bot_config()
        
        return {
            "status": "success",
            "config": config,
            "service": "grid",
            "message": "Configuración actual del grid bot"
        }
    except Exception as e:
        logger.error(f"❌ Error al obtener configuración del grid bot: {e}")
        return {
            "status": "error",
            "message": f"Error al obtener configuración: {str(e)}",
            "service": "grid"
        }

@router.post("/reset", tags=["Grid Trading"])
def reset_grid_bot():
    """
    Fuerza un reset completo del grid trading bot.
    ⚠️ ATENCIÓN: Esto cancelará todas las órdenes activas.
    """
    try:
        logger.warning("🚨 Iniciando reset forzado del Grid Bot vía API...")
        
        # Obtener configuración actual
        config = get_grid_bot_config()
        
        # Ejecutar reset forzado
        force_reset_bot(config)
        
        return {
            "status": "success",
            "message": "Grid Bot reseteado exitosamente",
            "warning": "Todas las órdenes activas han sido canceladas",
            "service": "grid"
        }
    except Exception as e:
        logger.error(f"❌ Error al resetear grid bot: {e}")
        return {
            "status": "error",
            "message": f"Error durante el reset: {str(e)}",
            "service": "grid"
        }

@router.get("/health", tags=["Grid Trading"])
def grid_health_check():
    """
    Health check específico para el grid trading service.
    """
    try:
        scheduler = get_grid_scheduler()
        
        health_data = {
            "service": "grid",
            "scheduler": {
                "running": scheduler.running if scheduler else False,
                "jobs_count": len(scheduler.get_jobs()) if scheduler and scheduler.running else 0
            }
        }
        
        # Determinar estado general
        if scheduler and scheduler.running:
            health_data["status"] = "healthy"
            health_data["message"] = "Grid trading service operativo"
        else:
            health_data["status"] = "degraded"
            health_data["message"] = "Scheduler no está ejecutándose"
        
        return health_data
        
    except Exception as e:
        logger.error(f"❌ Error en health check del grid: {e}")
        return {
            "service": "grid",
            "status": "error",
            "message": f"Error en health check: {str(e)}"
        } 