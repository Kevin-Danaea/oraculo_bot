"""
Módulo de integración con el servicio Cerebro
Gestiona el estado y comunicación con el motor de decisiones
"""

import httpx
import asyncio
from typing import Dict, Optional, Any
from shared.services.logging_config import get_logger
from shared.config.settings import settings

logger = get_logger(__name__)

# Estado del cerebro para integración
estado_cerebro = {
    "decision": "No disponible",
    "ultima_actualizacion": None,
    "fuente": "no_inicializado"
}

# Variable global para controlar modo productivo/sandbox
MODO_PRODUCTIVO = False  # False = Sandbox/Paper Trading (por defecto), True = Productivo

async def consultar_estado_inicial_cerebro():
    """
    Consulta el estado inicial del cerebro para el par configurado.
    
    Returns:
        Dict con la decisión del cerebro
    """
    global estado_cerebro
    
    try:
        # Por ahora, usar ETH/USDT como par por defecto
        # En el futuro, esto se puede mejorar para obtener la configuración del usuario
        par = "ETH/USDT"
        
        # Consultar al cerebro
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8004/grid/status/{par.replace('/', '-')}",
                timeout=60.0  # Aumentar timeout a 60 segundos para dar tiempo al cerebro
            )
            
            if response.status_code == 200:
                resultado = response.json()
                
                # Actualizar estado global
                estado_cerebro.update({
                    "decision": resultado.get('decision', 'No disponible'),
                    "ultima_actualizacion": resultado.get('timestamp'),
                    "fuente": resultado.get('fuente', 'consulta_manual')
                })
                
                logger.info(f"✅ Estado del cerebro consultado: {par} -> {resultado.get('decision')}")
                return resultado
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"❌ Error consultando cerebro: {e}")
        # No fallar si el cerebro no está disponible, solo retornar None
        return None

def obtener_configuracion_trading():
    """
    Retorna la configuración de trading según el modo activo
    """
    global MODO_PRODUCTIVO
    
    if MODO_PRODUCTIVO:
        return {
            "api_key": settings.BINANCE_API_KEY,
            "api_secret": settings.BINANCE_API_SECRET,
            "modo": "PRODUCTIVO",
            "descripcion": "Trading real en Binance"
        }
    else:
        return {
            "api_key": settings.PAPER_TRADING_API_KEY,
            "api_secret": settings.PAPER_TRADING_SECRET_KEY,
            "modo": "SANDBOX",
            "descripcion": "Paper trading para pruebas"
        }

def obtener_configuraciones_bd(chat_id: str = "default"):
    """
    Obtiene las configuraciones de la base de datos para el usuario.
    Funciona tanto en modo sandbox como productivo.
    
    Args:
        chat_id: ID del chat/usuario (default: "default")
               "all" para obtener todas las configuraciones activas
        
    Returns:
        Lista de configuraciones activas
    """
    try:
        from shared.database.session import get_db_session
        from shared.database.models import GridBotConfig
        
        with get_db_session() as db:
            # Si chat_id es "all", obtener todas las configuraciones activas
            if chat_id == "all":
                configs = db.query(GridBotConfig).filter(
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                ).all()
                logger.info(f"🔍 Obteniendo TODAS las configuraciones activas")
            else:
                # Buscar configuraciones existentes para este chat_id específico
                configs = db.query(GridBotConfig).filter(
                    GridBotConfig.telegram_chat_id == chat_id,
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                ).all()
            
            if chat_id == "all":
                logger.info(f"📊 Configuraciones encontradas: {len(configs)}")
                
                if not configs:
                    logger.warning("⚠️ No se encontraron configuraciones activas en el sistema")
                    return []
                else:
                    logger.info(f"✅ Configuraciones activas encontradas en el sistema")
            else:
                logger.info(f"🔍 Buscando configuraciones para chat_id: {chat_id}")
                logger.info(f"📊 Configuraciones encontradas: {len(configs)}")
                
                # Si no hay configuraciones, crear las por defecto SOLO si es necesario
                if not configs:
                    logger.info(f"⚠️ No se encontraron configuraciones para {chat_id}")
                    # NO crear configuraciones por defecto automáticamente
                    # El usuario debe configurar manualmente con /config
                    logger.info(f"💡 Usar /config para configurar los pares manualmente")
                    return []
                else:
                    logger.info(f"✅ Configuraciones existentes encontradas para {chat_id}")
            
            configuraciones = []
            for config in configs:
                configuraciones.append({
                    'pair': config.pair,
                    'config_type': config.config_type,
                    'total_capital': config.total_capital,
                    'grid_levels': config.grid_levels,
                    'price_range_percent': config.price_range_percent,
                    'last_decision': getattr(config, 'last_decision', 'NO_DECISION'),
                    'is_running': getattr(config, 'is_running', False),
                    'telegram_chat_id': config.telegram_chat_id
                })
            
            if chat_id == "all":
                logger.info(f"✅ Configuraciones obtenidas de BD: {len(configuraciones)} configs totales")
            else:
                logger.info(f"✅ Configuraciones obtenidas de BD: {len(configuraciones)} configs para {chat_id}")
            return configuraciones
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuraciones de BD: {e}")
        return []

def crear_configuraciones_por_defecto(db, chat_id: str = "default"):
    """
    Crea las configuraciones por defecto para los 3 pares soportados.
    
    Args:
        db: Sesión de base de datos
        chat_id: ID del chat/usuario
        
    Returns:
        Lista de configuraciones creadas
    """
    try:
        from shared.database.models import GridBotConfig
        from datetime import datetime
        
        configuraciones_por_defecto = [
            {
                'config_type': 'ETH',
                'pair': 'ETH/USDT',
                'total_capital': 1000.0,
                'grid_levels': 30,
                'price_range_percent': 10.0
            },
            {
                'config_type': 'BTC',
                'pair': 'BTC/USDT',
                'total_capital': 1000.0,
                'grid_levels': 30,
                'price_range_percent': 7.5
            },
            {
                'config_type': 'AVAX',
                'pair': 'AVAX/USDT',
                'total_capital': 1000.0,
                'grid_levels': 30,
                'price_range_percent': 10.0
            }
        ]
        
        configs_creadas = []
        
        for config_data in configuraciones_por_defecto:
            # Verificar si ya existe
            existing = db.query(GridBotConfig).filter(
                GridBotConfig.telegram_chat_id == chat_id,
                GridBotConfig.config_type == config_data['config_type']
            ).first()
            
            if not existing:
                # Crear nueva configuración
                nueva_config = GridBotConfig(
                    telegram_chat_id=chat_id,
                    config_type=config_data['config_type'],
                    pair=config_data['pair'],
                    total_capital=config_data['total_capital'],
                    grid_levels=config_data['grid_levels'],
                    price_range_percent=config_data['price_range_percent'],
                    stop_loss_percent=5.0,
                    enable_stop_loss=True,
                    enable_trailing_up=True,
                    is_active=True,
                    is_configured=True,
                    is_running=False,
                    last_decision='NO_DECISION',
                    last_decision_timestamp=datetime.utcnow()
                )
                db.add(nueva_config)
                configs_creadas.append(nueva_config)
                logger.info(f"✅ Configuración creada: {config_data['pair']} con ${config_data['total_capital']}")
            else:
                # Actualizar configuración existente
                existing.is_active = True
                existing.is_configured = True
                existing.total_capital = config_data['total_capital']
                configs_creadas.append(existing)
                logger.info(f"✅ Configuración actualizada: {config_data['pair']} con ${config_data['total_capital']}")
        
        db.commit()
        logger.info(f"✅ {len(configs_creadas)} configuraciones por defecto creadas/actualizadas para {chat_id}")
        
        return configs_creadas
        
    except Exception as e:
        logger.error(f"❌ Error creando configuraciones por defecto: {e}")
        db.rollback()
        return []

def consultar_cerebro_batch() -> Optional[Dict[str, Any]]:
    """
    Consulta el análisis batch del cerebro para obtener todas las decisiones de una vez.
    Mejora la eficiencia al evitar múltiples llamadas individuales.
    
    Returns:
        Diccionario con todas las decisiones del cerebro o None si hay error
    """
    try:
        import httpx
        import asyncio
        
        logger.info("🚀 ========== CONSULTANDO ANÁLISIS BATCH DEL CEREBRO ==========")
        
        # URL del endpoint batch del cerebro
        cerebro_url = "http://localhost:8004/grid/batch/analysis"
        
        # Función async para hacer la consulta
        async def fetch_batch_analysis():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(cerebro_url, timeout=60.0)  # Aumentar timeout a 60 segundos
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Análisis batch recibido: {data.get('summary', {})}")
                        return data
                    else:
                        logger.error(f"❌ Error en análisis batch: {response.status_code} - {response.text}")
                        return None
                        
            except httpx.ConnectError:
                logger.error(f"❌ No se puede conectar al cerebro en {cerebro_url}")
                return None
            except Exception as e:
                logger.error(f"❌ Error consultando análisis batch: {e}")
                return None
        
        # Ejecutar la consulta async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si el loop está corriendo, usar create_task
                task = loop.create_task(fetch_batch_analysis())
                # Esperar un poco para obtener el resultado
                import time
                time.sleep(2)
                return {"status": "processing", "message": "Análisis batch iniciado"}
            else:
                # Si el loop no está corriendo, ejecutar directamente
                return loop.run_until_complete(fetch_batch_analysis())
        except RuntimeError:
            # No hay event loop, crear uno nuevo
            return asyncio.run(fetch_batch_analysis())
            
    except Exception as e:
        logger.error(f"❌ Error en consulta batch: {e}")
        return {"error": str(e)}

def procesar_decisiones_batch(batch_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Procesa las decisiones del análisis batch del cerebro.
    
    Args:
        batch_data: Datos del análisis batch del cerebro
        
    Returns:
        Diccionario con decisiones procesadas por par
    """
    try:
        if not batch_data or batch_data.get('status') != 'success':
            logger.error("❌ Datos de análisis batch inválidos")
            return {}
        
        resultados = batch_data.get('results', {})
        decisiones_procesadas = {}
        
        logger.info(f"📊 Procesando {len(resultados)} decisiones del análisis batch...")
        
        for par, resultado in resultados.items():
            if resultado.get('success', False):
                decision = resultado.get('decision', 'ERROR')
                razon = resultado.get('razon', 'Sin razón')
                indicadores = resultado.get('indicadores', {})
                
                decisiones_procesadas[par] = {
                    'decision': decision,
                    'razon': razon,
                    'indicadores': indicadores,
                    'timestamp': resultado.get('timestamp'),
                    'success': True
                }
                
                logger.info(f"✅ {par}: {decision} - {razon}")
            else:
                logger.error(f"❌ {par}: Error en análisis - {resultado.get('error', 'Error desconocido')}")
                decisiones_procesadas[par] = {
                    'decision': 'ERROR',
                    'razon': resultado.get('error', 'Error desconocido'),
                    'success': False
                }
        
        # Resumen
        summary = batch_data.get('summary', {})
        logger.info(f"📈 Resumen batch: {summary}")
        
        return decisiones_procesadas
        
    except Exception as e:
        logger.error(f"❌ Error procesando decisiones batch: {e}")
        return {}

def consultar_y_procesar_cerebro_batch() -> Dict[str, Dict[str, Any]]:
    """
    Función combinada que consulta el cerebro batch y procesa las decisiones.
    
    Returns:
        Diccionario con decisiones procesadas por par
    """
    try:
        logger.info("🔄 Consultando y procesando análisis batch del cerebro...")
        
        # Consultar análisis batch
        batch_data = consultar_cerebro_batch()
        
        if not batch_data or batch_data.get('status') != 'success':
            logger.warning("⚠️ No se pudo obtener análisis batch, usando consultas individuales")
            return {}
        
        # Procesar decisiones
        decisiones = procesar_decisiones_batch(batch_data)
        
        logger.info(f"✅ Análisis batch completado: {len(decisiones)} decisiones procesadas")
        
        return decisiones
        
    except Exception as e:
        logger.error(f"❌ Error en consulta y procesamiento batch: {e}")
        return {}

def alternar_modo_trading():
    """
    Alterna entre modo productivo y sandbox
    Retorna el nuevo modo y configuración
    """
    global MODO_PRODUCTIVO
    MODO_PRODUCTIVO = not MODO_PRODUCTIVO
    
    config = obtener_configuracion_trading()
    logger.info(f"🔄 Modo cambiado a: {config['modo']}")
    
    return config

__all__ = [
    'estado_cerebro',
    'MODO_PRODUCTIVO',
    'consultar_estado_inicial_cerebro',
    'obtener_configuracion_trading',
    'obtener_configuraciones_bd',
    'consultar_cerebro_batch',
    'procesar_decisiones_batch',
    'consultar_y_procesar_cerebro_batch',
    'alternar_modo_trading'
] 