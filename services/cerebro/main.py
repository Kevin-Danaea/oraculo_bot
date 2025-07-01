#!/usr/bin/env python3
"""
Servicio Cerebro - Motor de Decisiones de Trading
================================================

Servicio principal que implementa el bucle de análisis continuo
para tomar decisiones de trading basadas en indicadores técnicos.

NUEVA ARQUITECTURA:
- Cerebro es PROACTIVO: notifica al Grid cuando cambiar
- Grid consulta estado inicial al arrancar
- Cerebro monitorea continuamente y avisa cambios
"""

import logging
import sys
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from typing import Dict, Optional

from .core.settings import (
    INTERVALO_ANALISIS,
    LOG_LEVEL,
    GRID_SERVICE_URL
)
from .core.recipe_master import PARES_A_MONITOREAR
from .core.decision_engine import DecisionEngine
from .core.multibot_notifier import get_multibot_notifier
from .routers import health_router
from .service import CerebroService

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cerebro_service.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# INSTANCIA GLOBAL DEL SERVICIO
# ============================================================================

cerebro_service = CerebroService()

# ============================================================================
# LIFECYCLE MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manager del ciclo de vida de la aplicación."""
    # Startup
    try:
        logger.info("🎯 ========== INICIANDO SERVICIO CEREBRO MULTIBOT ==========")
        logger.info("🧠 Servicio Cerebro - Motor de Decisiones Multibot (Arquitectura Proactiva)")
        logger.info("📋 Configuración Multibot:")
        logger.info(f"   📊 Pares monitoreados: {len(PARES_A_MONITOREAR)}")
        logger.info(f"   🔢 Pares: {', '.join(PARES_A_MONITOREAR)}")
        logger.info(f"   ⏰ Intervalo: {INTERVALO_ANALISIS}s")
        logger.info(f"   📁 Log level: {LOG_LEVEL}")
        logger.info(f"   🔗 Grid Service: {GRID_SERVICE_URL}")
        logger.info("🧠 Recetas maestras activadas para cada par")
        logger.info("⏸️ MODO STANDBY: Esperando primera conexión del Grid para iniciar monitoreo...")
        
        # El servicio se inicia, pero el bucle de análisis no.
        # El bucle se activará cuando el grid se conecte por primera vez.
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Servicio Cerebro: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("🛑 Deteniendo Servicio Cerebro...")
        await cerebro_service.stop()
        logger.info("✅ Servicio Cerebro detenido correctamente")
    except Exception as e:
        logger.error(f"❌ Error al detener Servicio Cerebro: {e}")

# ============================================================================
# APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="Servicio Cerebro - Motor de Decisiones Multibot",
    description="""
    Servicio que actúa como el "cerebro" del sistema de trading multibot.
    
    ## Nueva Arquitectura Multibot Proactiva
    
    * **Análisis Automático**: Monitorea 3 pares simultáneamente (ETH, BTC, AVAX)
    * **Recetas Maestras**: Cada par tiene condiciones específicas optimizadas
    * **Notificación Proactiva**: Avisa al Grid Multibot cuando cambiar decisiones  
    * **Sistema Escalable**: Fácil agregar nuevos pares en el futuro
    * **Decisiones Basadas en ADX, Volatilidad y Sentimiento**: Lógica optimizada
    
    ## Pares Monitoreados
    
    * **ETH/USDT**: ADX < 30, Bollinger > 0.025, Rango 10%
    * **BTC/USDT**: ADX < 25, Bollinger > 0.035, Rango 7.5%
    * **AVAX/USDT**: ADX < 35, Bollinger > 0.020, Rango 10%
    
    ## Análisis Automático
    
    * **Frecuencia**: Cada 1 hora
    * **Modo**: Análisis batch de todos los pares simultáneamente
    * **Notificación**: Proactiva al Grid cuando cambian las decisiones
    
    ## Endpoints Disponibles
    
    * **GET /**: Información del servicio
    * **GET /grid/status/{par}**: Consulta estado actual para Grid (inicial)
    * **GET /grid/multibot/status**: Estado completo del sistema multibot
    * **GET /recipes/master**: Información detallada de las recetas maestras
    * **GET /health/**: Health check del servicio
    """,
    version="3.0.0",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "dev@oraculo-bot.com"
    },
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(health_router)

# ============================================================================
# ENDPOINTS PRINCIPALES
# ============================================================================

@app.get("/")
async def root():
    """
    Endpoint raíz del servicio.
    
    Returns:
        Información básica del servicio
    """
    status = cerebro_service.get_status()
    return {
        "servicio": "Cerebro - Motor de Decisiones Multibot",
        "version": "3.0.0",
        "arquitectura": "Multibot Proactiva",
        "estado": "monitoreo_activo" if status['is_running'] else "standby",
        "grid_conectado": status['grid_is_connected'],
        "descripcion": "Servicio de análisis continuo que monitorea 3 pares simultáneamente",
        "pares_monitoreados": PARES_A_MONITOREAR,
        "total_pares": len(PARES_A_MONITOREAR),
        "intervalo_analisis": f"{INTERVALO_ANALISIS}s" if 'INTERVALO_ANALISIS' in globals() else "N/A",
        "grid_service_url": GRID_SERVICE_URL,
        "modo": "Monitoreo continuo activo" if status['is_running'] else "Esperando primera conexión del Grid",
        "frecuencia": f"Cada {INTERVALO_ANALISIS}s" if 'INTERVALO_ANALISIS' in globals() else "N/A",
        "analisis_batch": "Activado - todos los pares simultáneamente",
        "recetas_maestras": {
            "ETH/USDT": "ADX < 30, Bollinger > 0.025, Rango 10%",
            "BTC/USDT": "ADX < 25, Bollinger > 0.035, Rango 7.5%",
            "AVAX/USDT": "ADX < 35, Bollinger > 0.020, Rango 10%"
        },
        "endpoints": {
            "health": "/health/",
            "grid_consulta": "/grid/status/{par} (usar ETH-USDT)",
            "grid_batch": "/grid/batch/analysis (análisis de todos los pares)",
            "multibot_status": "/grid/multibot/status",
            "recipes_master": "/recipes/master",
            "documentacion": "/docs"
        }
    }

@app.get("/grid/status/{par}")
async def consultar_estado_inicial_grid(par: str):
    """
    Endpoint para que Grid consulte el estado inicial al arrancar.
    
    NUEVA LÓGICA:
    - Primera vez: activa el monitoreo continuo del cerebro
    - Siguientes veces: solo devuelve estado actual
    
    Args:
        par: Par de trading en formato con guiones (ej: 'ETH-USDT')
        
    Returns:
        Estado actual del par para inicialización del Grid
    """
    try:
        # Normalizar par de guiones a slashes internamente
        par_normalizado = par.replace('-', '/').upper()
        
        # La primera vez que se llama, se activa el monitoreo
        if not cerebro_service.grid_is_connected:
            await cerebro_service.start()

        response = await cerebro_service.analyze_pair_for_grid_startup(par_normalizado)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error consultando estado inicial para {par}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@app.get("/grid/multibot/status")
async def get_multibot_status():
    """
    Endpoint para obtener el estado completo del sistema multibot.
    
    Returns:
        Estado actual de todas las configuraciones del grid
    """
    try:
        notifier = get_multibot_notifier()
        status = notifier.get_grid_status_summary()
        
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat(),
            "total_pairs_monitored": len(PARES_A_MONITOREAR),
            "pairs_monitored": PARES_A_MONITOREAR
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado multibot: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estado multibot: {str(e)}"
        )

@app.get("/recipes/master")
async def get_master_recipes():
    """
    Endpoint para obtener información detallada de las recetas maestras.
    
    Returns:
        Información detallada de todas las recetas maestras
    """
    try:
        from .core.recipe_master import RecipeMaster
        
        recipes_summary = RecipeMaster.get_recipe_summary()
        
        return {
            "status": "success",
            "recipes": recipes_summary,
            "total_recipes": len(recipes_summary),
            "supported_pairs": RecipeMaster.get_all_supported_pairs(),
            "timestamp": datetime.now().isoformat(),
            "description": "Recetas maestras optimizadas por backtesting para cada par"
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo recetas maestras: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo recetas maestras: {str(e)}"
        )

@app.get("/grid/batch/analysis")
async def get_batch_analysis(force: bool = False):
    """
    Endpoint para obtener análisis batch de todos los pares de una vez.
    Si force=true, ejecuta un análisis nuevo. Si no, devuelve el último resultado cacheado.
    """
    try:
        response = await cerebro_service.get_batch_analysis(force)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en análisis batch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis batch: {str(e)}"
        )

@app.get("/grid/batch/init")
async def grid_batch_init():
    """
    Endpoint para inicializar el monitoreo batch y devolver el primer análisis.
    """
    try:
        if cerebro_service.is_running():
            logger.info("✅ Cerebro ya está activo. Devolviendo último análisis cacheado.")
            return await cerebro_service.get_batch_analysis(force=False)

        # Inicia el servicio, que correrá el primer análisis y luego el bucle.
        response = await cerebro_service.start()
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en batch init: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en batch init: {str(e)}")

# ============================================================================
# FUNCIONES DE CONTROL DEL SERVICIO
# ============================================================================

def start_cerebro_service():
    """
    Inicia el servicio cerebro en modo standalone.
    
    Returns:
        Instancia de la aplicación FastAPI
    """
    logger.info("🧠 Servicio Cerebro iniciado en modo standalone")
    # Iniciar el bucle de análisis en modo standalone
    asyncio.create_task(cerebro_service.start())
    return app

def stop_cerebro_service():
    """
    Detiene el servicio cerebro limpiamente.
    """
    logger.info("🛑 Deteniendo Servicio Cerebro...")
    asyncio.create_task(cerebro_service.stop())
    logger.info("✅ Servicio Cerebro detenido correctamente")

# ============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    # Punto de entrada directo (sin uvicorn - eso lo maneja run_cerebro_service.py)
    try:
        start_cerebro_service()
        
        # Mantener el servicio corriendo
        import time
        logger.info("🧠 Cerebro Worker ejecutándose en modo standalone...")
        while True:
            time.sleep(60)  # Revisar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción manual recibida...")
        stop_cerebro_service()
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        stop_cerebro_service()
        raise 