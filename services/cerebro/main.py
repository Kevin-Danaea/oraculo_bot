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
from .core.multibot_notifier import get_multibot_notifier
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

# ================== CACHÉ DEL ÚLTIMO ANÁLISIS BATCH =====================
ultimo_resultado_batch: Optional[Dict] = None
ultimo_batch_timestamp: Optional[datetime] = None

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
    
    NUEVA LÓGICA BATCH:
    1. Analiza TODOS los pares de una vez
    2. Compara con decisiones anteriores
    3. Notifica al Grid con todas las decisiones de una vez
    4. Actualiza base de datos
    """
    global bucle_activo, decisiones_anteriores, ultimo_resultado_batch, ultimo_batch_timestamp
    
    logger.info("🚀 ========== INICIANDO BUCLE PRINCIPAL DE ANÁLISIS MULTIBOT BATCH ==========")
    logger.info(f"📊 Pares a monitorear: {PARES_A_MONITOREAR}")
    logger.info(f"🔢 Total pares: {len(PARES_A_MONITOREAR)}")
    logger.info(f"⏰ Intervalo de análisis: {INTERVALO_ANALISIS} segundos")
    logger.info(f"🔗 URL Grid Service: {GRID_SERVICE_URL}")
    logger.info("🧠 Sistema multibot con análisis BATCH activado")
    logger.info("=" * 70)
    
    ciclo_numero = 0
    
    while bucle_activo:
        try:
            ciclo_numero += 1
            logger.info(f"🔄 ========== INICIANDO CICLO BATCH #{ciclo_numero} ==========")
            logger.info(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # ANÁLISIS BATCH: Analizar todos los pares de una vez
            logger.info("🚀 Ejecutando análisis batch de todos los pares...")
            resultados_batch = decision_engine.analizar_todos_los_pares()
            # Guardar en caché el resultado y el timestamp
            ultimo_resultado_batch = resultados_batch
            ultimo_batch_timestamp = datetime.now()
            
            if not resultados_batch:
                logger.error("❌ Error en análisis batch - no se obtuvieron resultados")
                continue
            
            # Procesar resultados del análisis batch
            cambios_detectados = {}
            
            for par, resultado in resultados_batch.items():
                if not bucle_activo:  # Verificar si se debe detener
                    break
                
                if resultado.get('success', False):
                    decision_actual = resultado['decision']
                    razon = resultado['razon']
                    indicadores = resultado['indicadores']
                    
                    logger.info(f"✅ {par}: {decision_actual}")
                    logger.info(f"📝 Razón: {razon}")
                    logger.info(f"📊 ADX: {indicadores['adx_actual']:.2f}, Volatilidad: {indicadores['volatilidad_actual']:.4f}")
                    
                    # Detectar cambios
                    decision_anterior = decisiones_anteriores.get(par)
                    
                    if decision_anterior is None:
                        # Primera vez - registrar cambio
                        logger.info(f"🆕 Primera decisión para {par}: {decision_actual}")
                        cambios_detectados[par] = {
                            'decision': decision_actual,
                            'razon': razon,
                            'indicadores': indicadores
                        }
                        decisiones_anteriores[par] = decision_actual
                        
                    elif decision_anterior != decision_actual:
                        # Cambio detectado - registrar cambio
                        logger.info(f"🔄 CAMBIO DETECTADO en {par}: {decision_anterior} -> {decision_actual}")
                        cambios_detectados[par] = {
                            'decision': decision_actual,
                            'razon': razon,
                            'indicadores': indicadores
                        }
                        decisiones_anteriores[par] = decision_actual
                        
                    else:
                        # Sin cambios - solo log
                        logger.info(f"➡️ {par}: Sin cambios ({decision_actual})")
                        
                else:
                    logger.error(f"❌ Error en análisis de {par}: {resultado.get('error', 'Error desconocido')}")
            
            # NOTIFICACIÓN BATCH: Notificar todos los cambios de una vez
            # NOTA: Esta es la ÚNICA notificación al Grid para evitar duplicados
            # El decision_engine solo actualiza la BD, no notifica
            if cambios_detectados:
                logger.info(f"📢 Notificando {len(cambios_detectados)} cambios al Grid...")
                
                try:
                    notifier = get_multibot_notifier()
                    resultados_notificacion = await notifier.notify_all_decisions(cambios_detectados)
                    
                    exitosos = sum(1 for success in resultados_notificacion.values() if success)
                    logger.info(f"✅ Notificaciones enviadas: {exitosos}/{len(cambios_detectados)} exitosas")
                    
                except Exception as e:
                    logger.error(f"❌ Error en notificación batch: {e}")
            else:
                logger.info("ℹ️ No se detectaron cambios - no se envían notificaciones")
            
            logger.info(f"✅ ========== CICLO BATCH #{ciclo_numero} COMPLETADO ==========")
            
            if bucle_activo:
                logger.info(f"⏳ Esperando {INTERVALO_ANALISIS} segundos hasta el próximo ciclo...")
                await asyncio.sleep(INTERVALO_ANALISIS)
            
        except Exception as e:
            logger.error(f"💥 Error crítico en bucle principal batch: {str(e)}")
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
        logger.info("🎯 ========== INICIANDO SERVICIO CEREBRO MULTIBOT ==========")
        logger.info("🧠 Servicio Cerebro - Motor de Decisiones Multibot (Arquitectura Proactiva)")
        logger.info("📋 Configuración Multibot:")
        logger.info(f"   📊 Pares monitoreados: {len(PARES_A_MONITOREAR)}")
        logger.info(f"   🔢 Pares: {', '.join(PARES_A_MONITOREAR)}")
        logger.info(f"   ⏰ Intervalo: {INTERVALO_ANALISIS}s")
        logger.info(f"   📁 Log level: {LOG_LEVEL}")
        logger.info(f"   🔗 Grid Service: {GRID_SERVICE_URL}")
        logger.info("🧠 Recetas maestras activadas para cada par")
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
    return {
        "servicio": "Cerebro - Motor de Decisiones Multibot",
        "version": "3.0.0",
        "arquitectura": "Multibot Proactiva",
        "estado": "monitoreo_activo" if bucle_activo else "standby",
        "grid_conectado": grid_conectado_primera_vez,
        "descripcion": "Servicio de análisis continuo que monitorea 3 pares simultáneamente",
        "pares_monitoreados": PARES_A_MONITOREAR,
        "total_pares": len(PARES_A_MONITOREAR),
        "intervalo_analisis": f"{INTERVALO_ANALISIS}s",
        "grid_service_url": GRID_SERVICE_URL,
        "modo": "Esperando primera conexión del Grid" if not grid_conectado_primera_vez else "Monitoreo continuo activo",
        "frecuencia": "Cada 1 hora (3600s)",
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
    global ultimo_resultado_batch, ultimo_batch_timestamp
    try:
        if force or ultimo_resultado_batch is None:
            logger.info("🚀 Ejecutando análisis batch (forzado o primer uso)...")
            resultados_batch = decision_engine.analizar_todos_los_pares()
            ultimo_resultado_batch = resultados_batch
            ultimo_batch_timestamp = datetime.now()
        else:
            logger.info(f"ℹ️ Devolviendo resultado batch cacheado (timestamp: {ultimo_batch_timestamp})")
            resultados_batch = ultimo_resultado_batch

        if not resultados_batch:
            raise HTTPException(
                status_code=500,
                detail="Error ejecutando análisis batch"
            )
        # Preparar respuesta
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "batch_cached_at": ultimo_batch_timestamp.isoformat() if ultimo_batch_timestamp else None,
            "total_pairs": len(resultados_batch),
            "pairs_analyzed": list(resultados_batch.keys()),
            "results": {},
            "summary": {
                "OPERAR_GRID": 0,
                "PAUSAR_GRID": 0,
                "ERROR": 0
            }
        }
        # Procesar resultados
        for par, resultado in resultados_batch.items():
            response["results"][par] = resultado
            if resultado.get('success', False):
                decision = resultado.get('decision', 'ERROR')
                response["summary"][decision] += 1
            else:
                response["summary"]["ERROR"] += 1
        logger.info(f"✅ Análisis batch entregado: {response['summary']}")
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
    Endpoint para inicializar el monitoreo batch y devolver el primer análisis de todos los pares.
    """
    global grid_conectado_primera_vez, ultimo_resultado_batch, ultimo_batch_timestamp

    if not grid_conectado_primera_vez:
        logger.info("🚀 ========== PRIMERA CONEXIÓN DEL GRID (BATCH) ==========")
        grid_conectado_primera_vez = True
        # Ejecutar análisis batch de todos los pares
        resultados_batch = decision_engine.analizar_todos_los_pares()
        ultimo_resultado_batch = resultados_batch
        ultimo_batch_timestamp = datetime.now()
        iniciar_bucle_analisis()
        logger.info("🔄 Monitoreo batch ACTIVADO")
    else:
        logger.info("ℹ️ Grid solicitó batch init pero ya está activo, devolviendo último batch cacheado.")
        resultados_batch = ultimo_resultado_batch

    if not resultados_batch:
        raise HTTPException(
            status_code=500,
            detail="Error ejecutando análisis batch"
        )

    # Preparar respuesta igual que en /grid/batch/analysis
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "batch_cached_at": ultimo_batch_timestamp.isoformat() if ultimo_batch_timestamp else None,
        "total_pairs": len(resultados_batch),
        "pairs_analyzed": list(resultados_batch.keys()),
        "results": {},
        "summary": {
            "OPERAR_GRID": 0,
            "PAUSAR_GRID": 0,
            "ERROR": 0
        }
    }
    for par, resultado in resultados_batch.items():
        response["results"][par] = resultado
        if resultado.get('success', False):
            decision = resultado.get('decision', 'ERROR')
            response["summary"][decision] += 1
        else:
            response["summary"]["ERROR"] += 1
    logger.info(f"✅ Batch init entregado: {response['summary']}")
    return response

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