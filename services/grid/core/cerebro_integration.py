"""
Módulo de integración con el servicio Cerebro
Gestiona el estado y comunicación con el motor de decisiones
"""

import httpx
import asyncio
from typing import Dict, Optional, Any
from shared.services.logging_config import get_logger

logger = get_logger(__name__)

# URL del servicio Cerebro, debería moverse a settings
CEREBRO_URL = "http://localhost:8004"

class CerebroClient:
    """
    Cliente para interactuar con el servicio Cerebro.
    """
    def __init__(self):
        self.estado_cerebro = {
            "decision": "No disponible",
            "ultima_actualizacion": None,
            "fuente": "no_inicializado"
        }

    async def consultar_estado_inicial(self, par: str = "ETH/USDT") -> Optional[Dict]:
        """
        Consulta el estado inicial del cerebro para el par configurado.
        
        Returns:
            Dict con la decisión del cerebro o None si hay error.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CEREBRO_URL}/grid/status/{par.replace('/', '-')}",
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    resultado = response.json()
                    self.estado_cerebro.update({
                        "decision": resultado.get('decision', 'No disponible'),
                        "ultima_actualizacion": resultado.get('timestamp'),
                        "fuente": resultado.get('fuente', 'consulta_manual')
                    })
                    logger.info(f"✅ Estado del cerebro consultado: {par} -> {resultado.get('decision')}")
                    return resultado
                else:
                    logger.error(f"Error consultando cerebro {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error consultando cerebro: {e}")
            return None

    async def consultar_analisis_batch(self) -> Optional[Dict[str, Any]]:
        """
        Consulta el análisis batch del cerebro para obtener todas las decisiones de una vez.
        """
        try:
            logger.info("🚀 ========== CONSULTANDO ANÁLISIS BATCH DEL CEREBRO ==========")
            cerebro_url = f"{CEREBRO_URL}/grid/batch/analysis"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(cerebro_url, timeout=60.0)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Análisis batch recibido: {data.get('summary', {})}")
                    return data
                else:
                    logger.error(f"❌ Error en análisis batch: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.ConnectError:
            logger.error(f"❌ No se puede conectar al cerebro en {CEREBRO_URL}")
            return None
        except Exception as e:
            logger.error(f"❌ Error consultando análisis batch: {e}")
            return None

    def procesar_decisiones_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Procesa las decisiones del análisis batch del cerebro.
        """
        if not batch_data or batch_data.get('status') != 'success':
            logger.error("❌ Datos de análisis batch inválidos")
            return {}
        
        resultados = batch_data.get('results', {})
        decisiones_procesadas = {}
        
        for par, resultado in resultados.items():
            if resultado.get('success', False):
                decisiones_procesadas[par] = {
                    'decision': resultado.get('decision', 'ERROR'),
                    'razon': resultado.get('razon', 'Sin razón'),
                    'indicadores': resultado.get('indicadores', {}),
                    'timestamp': resultado.get('timestamp'),
                    'success': True
                }
            else:
                decisiones_procesadas[par] = {
                    'decision': 'ERROR',
                    'razon': resultado.get('error', 'Error desconocido'),
                    'success': False
                }
        
        summary = batch_data.get('summary', {})
        logger.info(f"📈 Resumen batch: {summary}")
        
        return decisiones_procesadas

    async def consultar_y_procesar_batch(self) -> Dict[str, Dict[str, Any]]:
        """
        Función combinada que consulta el cerebro batch y procesa las decisiones.
        """
        batch_data = await self.consultar_analisis_batch()
        if not batch_data:
            return {}
        return self.procesar_decisiones_batch(batch_data)


# Singleton instance
cerebro_client = CerebroClient()

__all__ = [
    'cerebro_client'
] 