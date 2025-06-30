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

from .core.config import (
    PARES_A_MONITOREAR, 
    INTERVALO_ANALISIS,
    LOG_LEVEL
)
from .core.decision_engine import DecisionEngine
from .routers import health_router

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
# INSTANCIA GLOBAL DEL MOTOR DE DECISIONES
# ============================================================================

decision_engine = DecisionEngine()

# Variables de control del bucle
bucle_activo = False
task_bucle = None

# Tracking de decisiones anteriores para detectar cambios
decisiones_anteriores: Dict[str, str] = {}

# Estado de inicialización - el cerebro espera en standby
grid_conectado_primera_vez = False

# Configuración del servicio Grid
GRID_SERVICE_URL = "http://localhost:8001"  # Puerto del servicio Grid

# ============================================================================
# COMUNICACIÓN CON GRID SERVICE
# ============================================================================

async def notificar_grid(par: str, decision: str, razon: str):
    """
    Notifica al servicio Grid sobre un cambio de decisión.
    
    Args:
        par: Par de trading
        decision: Nueva decisión (OPERAR_GRID/PAUSAR_GRID)
        razon: Razón de la decisión
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "par": par,
                "decision": decision,
                "razon": razon,
                "timestamp": datetime.now().isoformat(),
                "fuente": "cerebro"
            }
            
            response = await client.post(
                f"{GRID_SERVICE_URL}/cerebro/decision",
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Grid notificado: {par} -> {decision}")
            else:
                logger.warning(f"⚠️ Error notificando Grid: {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Error comunicándose con Grid: {e}")
        # No falla el proceso principal si Grid no está disponible

# ============================================================================
# BUCLE PRINCIPAL DE ANÁLISIS
# ============================================================================

async def bucle_principal_analisis():
    """
    Bucle principal que ejecuta el análisis continuo de los pares monitoreados.
    
    NUEVA LÓGICA:
    1. Analiza cada par según umbrales configurados
    2. Compara con decisión anterior
    3. Si hay cambio, notifica al Grid automáticamente
    4. Actualiza base de datos
    """
    global bucle_activo, decisiones_anteriores
    
    logger.info("🚀 ========== INICIANDO BUCLE PRINCIPAL DE ANÁLISIS ==========")
    logger.info(f"📊 Pares a monitorear: {PARES_A_MONITOREAR}")
    logger.info(f"⏰ Intervalo de análisis: {INTERVALO_ANALISIS} segundos")
    logger.info(f"🔗 URL Grid Service: {GRID_SERVICE_URL}")
    logger.info("=" * 70)
    
    ciclo_numero = 0
    
    while bucle_activo:
        try:
            ciclo_numero += 1
            logger.info(f"🔄 ========== INICIANDO CICLO #{ciclo_numero} ==========")
            logger.info(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Iterar sobre cada par a monitorear
            for par in PARES_A_MONITOREAR:
                if not bucle_activo:  # Verificar si se debe detener
                    break
                
                try:
                    logger.info(f"🔍 Analizando {par}...")
                    
                    # Ejecutar análisis para este par
                    resultado = decision_engine.analizar_par(par)
                    
                    if resultado.get('success', False):
                        decision_actual = resultado['decision']
                        razon = resultado['razon']
                        indicadores = resultado['indicadores']
                        
                        logger.info(f"✅ {par}: {decision_actual}")
                        logger.info(f"📝 Razón: {razon}")
                        logger.info(f"📊 ADX: {indicadores['adx_actual']:.2f}, Volatilidad: {indicadores['volatilidad_actual']:.4f}")
                        
                        # NUEVA LÓGICA: Detectar cambios y notificar Grid
                        decision_anterior = decisiones_anteriores.get(par)
                        
                        if decision_anterior is None:
                            # Primera vez - siempre notificar
                            logger.info(f"🆕 Primera decisión para {par}: {decision_actual}")
                            await notificar_grid(par, decision_actual, razon)
                            decisiones_anteriores[par] = decision_actual
                            
                        elif decision_anterior != decision_actual:
                            # Cambio detectado - notificar Grid
                            logger.info(f"🔄 CAMBIO DETECTADO en {par}: {decision_anterior} -> {decision_actual}")
                            await notificar_grid(par, decision_actual, razon)
                            decisiones_anteriores[par] = decision_actual
                            
                        else:
                            # Sin cambios - solo log
                            logger.info(f"➡️ {par}: Sin cambios ({decision_actual})")
                        
                        if decision_actual == "OPERAR_GRID":
                            logger.info(f"🟢 {par}: Condiciones favorables para Grid Trading")
                        else:
                            logger.info(f"🔴 {par}: Pausar Grid Trading")
                            
                    else:
                        logger.error(f"❌ Error en análisis de {par}: {resultado.get('error', 'Error desconocido')}")
                    
                    logger.info(f"💾 Estado actualizado en base de datos para {par}")
                    
                except Exception as e:
                    logger.error(f"💥 Error analizando {par}: {str(e)}")
                    logger.info(f"⏭️ Continuando con el siguiente par...")
                    continue
            
            logger.info(f"✅ ========== CICLO #{ciclo_numero} COMPLETADO ==========")
            
            if bucle_activo:
                logger.info(f"⏳ Esperando {INTERVALO_ANALISIS} segundos hasta el próximo ciclo...")
                await asyncio.sleep(INTERVALO_ANALISIS)
            
        except Exception as e:
            logger.error(f"💥 Error crítico en bucle principal: {str(e)}")
            logger.info("🔄 Reintentando en 60 segundos...")
            if bucle_activo:
                await asyncio.sleep(60)

def iniciar_bucle_analisis():
    """Inicia el bucle de análisis en segundo plano."""
    global bucle_activo, task_bucle
    
    if not bucle_activo:
        bucle_activo = True
        task_bucle = asyncio.create_task(bucle_principal_analisis())
        logger.info("🚀 Bucle de análisis iniciado")
    else:
        logger.warning("⚠️ El bucle de análisis ya está activo")

def detener_bucle_analisis():
    """Detiene el bucle de análisis."""
    global bucle_activo, task_bucle
    
    if bucle_activo:
        bucle_activo = False
        if task_bucle:
            task_bucle.cancel()
        logger.info("🛑 Bucle de análisis detenido")
    else:
        logger.warning("⚠️ El bucle de análisis no está activo")

# ============================================================================
# LIFECYCLE MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manager del ciclo de vida de la aplicación."""
    # Startup
    try:
        logger.info("🎯 ========== INICIANDO SERVICIO CEREBRO ==========")
        logger.info("🧠 Servicio Cerebro - Motor de Decisiones (Arquitectura Proactiva)")
        logger.info("📋 Configuración:")
        logger.info(f"   📊 Pares monitoreados: {len(PARES_A_MONITOREAR)}")
        logger.info(f"   ⏰ Intervalo: {INTERVALO_ANALISIS}s")
        logger.info(f"   📁 Log level: {LOG_LEVEL}")
        logger.info(f"   🔗 Grid Service: {GRID_SERVICE_URL}")
        logger.info("⏸️ MODO STANDBY: Esperando primera conexión del Grid...")
        
        # NO iniciar bucle automáticamente - esperar a Grid
        logger.info("✅ Servicio Cerebro iniciado en modo standby")
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar Servicio Cerebro: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("🛑 Deteniendo Servicio Cerebro...")
        detener_bucle_analisis()
        logger.info("✅ Servicio Cerebro detenido correctamente")
    except Exception as e:
        logger.error(f"❌ Error al detener Servicio Cerebro: {e}")

# ============================================================================
# APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="Servicio Cerebro - Motor de Decisiones",
    description="""
    Servicio que actúa como el "cerebro" del sistema de trading.
    
    ## Nueva Arquitectura Proactiva
    
    * **Análisis Automático**: Monitorea pares 24/7 automáticamente
    * **Notificación Proactiva**: Avisa al Grid cuando cambiar decisiones  
    * **Consulta Inicial**: Grid puede consultar estado inicial al arrancar
    * **Decisiones Basadas en ADX y Volatilidad**: Lógica simple y efectiva
    
    ## Endpoints Disponibles
    
    * **GET /**: Información del servicio
    * **GET /grid/status/{par}**: Consulta estado actual para Grid (inicial)
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
    return {
        "servicio": "Cerebro - Motor de Decisiones",
        "version": "3.0.0",
        "arquitectura": "Proactiva",
        "estado": "monitoreo_activo" if bucle_activo else "standby",
        "grid_conectado": grid_conectado_primera_vez,
        "descripcion": "Servicio de análisis continuo que notifica al Grid automáticamente",
        "pares_monitoreados": PARES_A_MONITOREAR,
        "intervalo_analisis": f"{INTERVALO_ANALISIS}s",
        "grid_service_url": GRID_SERVICE_URL,
        "modo": "Esperando primera conexión del Grid" if not grid_conectado_primera_vez else "Monitoreo continuo activo",
        "endpoints": {
            "health": "/health/",
            "grid_consulta": "/grid/status/{par} (usar ETH-USDT)",
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
    global grid_conectado_primera_vez
    
    try:
        # Normalizar par de guiones a slashes internamente
        par_normalizado = par.replace('-', '/').upper()
        
        if not grid_conectado_primera_vez:
            logger.info("🚀 ========== PRIMERA CONEXIÓN DEL GRID DETECTADA ==========")
            logger.info(f"🔍 Grid consultando estado inicial para {par} -> {par_normalizado}")
            logger.info("🎯 Activando monitoreo continuo del cerebro...")
            
            # Marcar como conectado y activar monitoreo
            grid_conectado_primera_vez = True
            
            # Ejecutar análisis inmediato
            resultado = decision_engine.analizar_par(par_normalizado)
            
            if not resultado.get('success', False):
                raise HTTPException(
                    status_code=400,
                    detail=f"Error analizando {par_normalizado}: {resultado.get('error', 'Error desconocido')}"
                )
            
            decision = resultado['decision']
            razon = resultado['razon']
            
            # Actualizar tracking de decisiones
            decisiones_anteriores[par_normalizado] = decision
            
            # Iniciar el bucle de monitoreo continuo DESPUÉS del primer análisis
            logger.info("🔄 Iniciando bucle de monitoreo continuo...")
            iniciar_bucle_analisis()
            
            response = {
                "par": par_normalizado,
                "decision": decision,
                "razon": razon,
                "timestamp": datetime.now().isoformat(),
                "puede_operar": decision == "OPERAR_GRID",
                "fuente": "cerebro_primera_conexion",
                "monitoreo_activado": True
            }
            
            logger.info(f"✅ Primera conexión procesada: {par_normalizado} -> {decision}")
            logger.info("🔄 Monitoreo continuo ACTIVADO")
            
        else:
            # Consultas posteriores - solo devolver estado actual
            logger.info(f"🔍 Grid consultando estado para {par} -> {par_normalizado} (consulta posterior)")
            
            # Ejecutar análisis inmediato
            resultado = decision_engine.analizar_par(par_normalizado)
            
            if not resultado.get('success', False):
                raise HTTPException(
                    status_code=400,
                    detail=f"Error analizando {par_normalizado}: {resultado.get('error', 'Error desconocido')}"
                )
            
            decision = resultado['decision']
            razon = resultado['razon']
            
            response = {
                "par": par_normalizado,
                "decision": decision,
                "razon": razon,
                "timestamp": datetime.now().isoformat(),
                "puede_operar": decision == "OPERAR_GRID",
                "fuente": "cerebro_consulta_posterior",
                "monitoreo_activado": True
            }
            
            logger.info(f"✅ Estado enviado a Grid: {par_normalizado} -> {decision}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error consultando estado inicial para {par}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

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
    return app

def stop_cerebro_service():
    """
    Detiene el servicio cerebro limpiamente.
    """
    logger.info("🛑 Deteniendo Servicio Cerebro...")
    detener_bucle_analisis()
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