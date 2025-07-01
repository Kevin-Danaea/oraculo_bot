"""
Router de Status - Endpoints de estado del sistema
Incluye health checks de todos los microservicios workers.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.services.logging_config import get_logger
from shared.database.session import SessionLocal
from services.news.schedulers.news_scheduler import get_news_scheduler
from services.grid.schedulers.multibot_scheduler import get_multibot_scheduler
import requests
from typing import Dict, Any
import asyncio
import aiohttp

logger = get_logger(__name__)

# Crear el router
router = APIRouter()

# --- Dependencia para la sesión de DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configuración de servicios workers
WORKER_SERVICES = {
    "news": {
        "name": "News Worker",
        "url": "http://localhost:8000",
        "description": "Servicio de recolección de noticias y análisis de sentimientos"
    },
    "grid": {
        "name": "Grid Trading Worker", 
        "url": "http://localhost:8001",
        "description": "Servicio de trading automatizado con estrategia de grilla"
    }
}

async def check_worker_health(service_name: str, service_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verifica el estado de salud de un worker específico mediante HTTP.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5 segundos timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{service_config['url']}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "service": service_name,
                        "name": service_config["name"],
                        "status": "healthy",
                        "url": service_config["url"],
                        "response_time": "< 5s",
                        "details": data
                    }
                else:
                    return {
                        "service": service_name,
                        "name": service_config["name"],
                        "status": "unhealthy",
                        "url": service_config["url"],
                        "error": f"HTTP {response.status}"
                    }
    except asyncio.TimeoutError:
        return {
            "service": service_name,
            "name": service_config["name"],
            "status": "timeout",
            "url": service_config["url"],
            "error": "Timeout después de 5 segundos"
        }
    except Exception as e:
        return {
            "service": service_name,
            "name": service_config["name"],
            "status": "error",
            "url": service_config["url"],
            "error": str(e)
        }

@router.get("/health", tags=["System"])
async def system_health_check():
    """
    Health check completo del sistema - verifica todos los microservicios workers.
    Este endpoint actúa como agregador de estado para todo el sistema.
    """
    logger.info("🔍 Ejecutando health check completo del sistema...")
    
    # Verificar workers en paralelo
    health_checks = []
    for service_name, service_config in WORKER_SERVICES.items():
        health_checks.append(check_worker_health(service_name, service_config))
    
    # Ejecutar todos los health checks en paralelo
    worker_results = await asyncio.gather(*health_checks, return_exceptions=True)
    
    # Procesar resultados
    services_status = []
    all_healthy = True
    
    for result in worker_results:
        if isinstance(result, Exception):
            services_status.append({
                "service": "unknown",
                "status": "error",
                "error": str(result)
            })
            all_healthy = False
        else:
            services_status.append(result)
            if isinstance(result, dict) and result.get("status") != "healthy":
                all_healthy = False
    
    # Estado del API Gateway
    api_gateway_status = {
        "service": "api_gateway",
        "name": "API Gateway",
        "status": "healthy",
        "url": "http://localhost:8002",
        "description": "Gateway centralizado para todos los microservicios"
    }
    services_status.insert(0, api_gateway_status)
    
    # Respuesta final
    overall_status = "healthy" if all_healthy else "degraded"
    healthy_count = sum(1 for s in services_status if s.get("status") == "healthy")
    total_count = len(services_status)
    
    return {
        "system_status": overall_status,
        "timestamp": "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')",
        "summary": f"{healthy_count}/{total_count} servicios saludables",
        "services": services_status,
        "architecture": "microservices",
        "gateway_version": "v1.0"
    }

@router.get("/services", tags=["System"])
async def list_services():
    """
    Lista todos los microservicios del sistema con su información básica.
    """
    services = []
    
    # API Gateway
    services.append({
        "service": "api_gateway",
        "name": "API Gateway",
        "port": 8002,
        "status": "running",
        "description": "Gateway centralizado - punto único de entrada HTTP",
        "endpoints": ["/api/v1/health", "/api/v1/news/*", "/api/v1/grid/*"]
    })
    
    # Workers
    for service_name, config in WORKER_SERVICES.items():
        port = int(config["url"].split(":")[-1])
        services.append({
            "service": service_name,
            "name": config["name"], 
            "port": port,
            "status": "worker",
            "description": config["description"],
            "type": "background_worker"
        })
    
    return {
        "total_services": len(services),
        "architecture": "api_gateway + workers",
        "services": services
    }

@router.get("/", tags=["System"])
def system_status():
    """Estado general del sistema y información arquitectónica."""
    return {
        "system": "Oráculo Cripto Bot",
        "architecture": "Microservicios con API Gateway",
        "version": "2.0.0",
        "status": "operational",
        "components": {
            "api_gateway": "Centralized HTTP endpoints",
            "news_worker": "Reddit collection + Sentiment analysis", 
            "grid_worker": "Automated grid trading on Binance"
        },
        "health_check": "/api/v1/health",
        "documentation": "/docs"
    }

# --- Endpoints de Estado ---
@router.get("/", tags=["Status"])
def api_status():
    """Endpoint principal para verificar que la API está viva."""
    return {"status": "El Oráculo está vivo y escuchando.", "gateway": "active"}

@router.get("/health", tags=["Status"])
def health_status():
    """Health check detallado de todos los servicios."""
    try:
        services_status = {}
        
        # Verificar servicio de noticias
        try:
            news_scheduler = get_news_scheduler()
            services_status["news"] = {
                "status": "healthy" if news_scheduler and news_scheduler.running else "stopped",
                "scheduler_running": news_scheduler.running if news_scheduler else False
            }
        except Exception as e:
            services_status["news"] = {"status": "error", "error": str(e)}
        
        # Verificar servicio de grid
        try:
            grid_scheduler = get_multibot_scheduler()
            services_status["grid"] = {
                "status": "healthy" if grid_scheduler and grid_scheduler.scheduler.running else "stopped",
                "scheduler_running": grid_scheduler.scheduler.running if grid_scheduler else False
            }
        except Exception as e:
            services_status["grid"] = {"status": "error", "error": str(e)}
        
        # Estado general
        overall_status = "healthy" if all(
            svc.get("status") == "healthy" for svc in services_status.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "services": services_status,
            "gateway": "operational"
        }
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "gateway": "error"
        }

@router.get("/scheduler", tags=["Status"])
def scheduler_status():
    """
    Endpoint de diagnóstico para verificar el estado de todos los schedulers.
    Migrado desde el endpoint original status_scheduler.
    """
    try:
        all_schedulers = {}
        
        # Scheduler de noticias
        try:
            news_scheduler = get_news_scheduler()
            if news_scheduler and news_scheduler.running:
                news_jobs = []
                for job in news_scheduler.get_jobs():
                    job_data = {
                        "id": job.id,
                        "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    news_jobs.append(job_data)
                
                all_schedulers["news"] = {
                    "status": "running",
                    "jobs": news_jobs,
                    "jobs_count": len(news_jobs)
                }
            else:
                all_schedulers["news"] = {
                    "status": "stopped",
                    "jobs": [],
                    "jobs_count": 0
                }
        except Exception as e:
            all_schedulers["news"] = {
                "status": "error",
                "error": str(e),
                "jobs": [],
                "jobs_count": 0
            }
        
        # Scheduler de grid
        try:
            grid_scheduler = get_multibot_scheduler()
            if grid_scheduler and grid_scheduler.scheduler.running:
                grid_jobs = []
                for job in grid_scheduler.scheduler.get_jobs():
                    job_data = {
                        "id": job.id,
                        "name": job.name or job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    grid_jobs.append(job_data)
                
                all_schedulers["grid"] = {
                    "status": "running",
                    "jobs": grid_jobs,
                    "jobs_count": len(grid_jobs)
                }
            else:
                all_schedulers["grid"] = {
                    "status": "stopped", 
                    "jobs": [],
                    "jobs_count": 0
                }
        except Exception as e:
            all_schedulers["grid"] = {
                "status": "error",
                "error": str(e),
                "jobs": [],
                "jobs_count": 0
            }
        
        # Resumen general
        total_jobs = sum(sch.get("jobs_count", 0) for sch in all_schedulers.values())
        running_schedulers = sum(1 for sch in all_schedulers.values() if sch.get("status") == "running")
        
        return {
            "status": "healthy" if running_schedulers > 0 else "no_schedulers_running",
            "summary": {
                "total_schedulers": len(all_schedulers),
                "running_schedulers": running_schedulers,
                "total_jobs": total_jobs
            },
            "schedulers": all_schedulers
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener estado de schedulers: {e}")
        return {
            "status": "error",
            "error": str(e),
            "schedulers": {}
        } 