"""
Módulo de integración con el servicio Cerebro
Gestiona el estado y comunicación con el motor de decisiones
"""

import httpx
import asyncio
from typing import Dict, Optional
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
MODO_PRODUCTIVO = True  # True = Productivo, False = Sandbox/Paper Trading

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
                timeout=10.0
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
        raise

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
    'alternar_modo_trading'
] 