"""
Multibot Notifier - Notificaciones al Grid Multibot
==================================================

Módulo para notificar al servicio Grid sobre cambios en las decisiones
del cerebro para el sistema multibot simultáneo.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from shared.services.logging_config import get_logger
from shared.database.session import get_db_session
from shared.database.models import GridBotConfig

logger = get_logger(__name__)

class MultibotNotifier:
    """
    Maneja las notificaciones al grid multibot cuando cambian las decisiones del cerebro.
    """
    
    def __init__(self, grid_service_url: str = "http://localhost:8001"):
        """
        Inicializa el notificador multibot.
        
        Args:
            grid_service_url: URL del servicio Grid
        """
        self.grid_service_url = grid_service_url
        self.logger = get_logger(__name__)
        
    async def notify_grid_decision_change(
        self, 
        pair: str, 
        decision: str, 
        razon: str,
        indicadores: Dict[str, Any]
    ) -> bool:
        """
        Notifica al grid sobre un cambio de decisión para un par específico.
        
        Args:
            pair: Par de trading (ej: 'ETH/USDT')
            decision: Nueva decisión ('OPERAR_GRID' o 'PAUSAR_GRID')
            razon: Razón de la decisión
            indicadores: Indicadores utilizados para la decisión
            
        Returns:
            True si la notificación fue exitosa
        """
        try:
            # 1. Actualizar la base de datos con la nueva decisión
            self._update_grid_config_decision(pair, decision)
            
            # 2. Notificar al grid service via API
            success = await self._notify_grid_api(pair, decision, razon, indicadores)
            
            if success:
                self.logger.info(f"✅ Grid notificado exitosamente: {pair} -> {decision}")
            else:
                self.logger.warning(f"⚠️ Grid no disponible, pero decisión guardada en BD: {pair} -> {decision}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error notificando grid para {pair}: {e}")
            return False
    
    def _update_grid_config_decision(self, pair: str, decision: str):
        """
        Actualiza la decisión en la tabla grid_bot_config.
        
        Args:
            pair: Par de trading
            decision: Nueva decisión
        """
        try:
            with get_db_session() as db:
                # Buscar configuraciones activas para este par
                configs = db.query(GridBotConfig).filter(
                    GridBotConfig.pair == pair,
                    GridBotConfig.is_active == True
                ).all()
                
                if not configs:
                    self.logger.warning(f"⚠️ No se encontraron configuraciones activas para {pair}")
                    return
                
                # Actualizar todas las configuraciones activas para este par
                for config in configs:
                    setattr(config, "last_decision", decision)
                    setattr(config, "last_decision_timestamp", datetime.utcnow())
                    self.logger.info(f"💾 Decisión actualizada en BD: {pair} -> {decision}")
                
                db.commit()
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando decisión en BD para {pair}: {e}")
            raise
    
    async def _notify_grid_api(
        self, 
        pair: str, 
        decision: str, 
        razon: str,
        indicadores: Dict[str, Any]
    ) -> bool:
        """
        Notifica al grid service via API REST.
        
        Args:
            pair: Par de trading
            decision: Nueva decisión
            razon: Razón de la decisión
            indicadores: Indicadores utilizados
            
        Returns:
            True si la notificación fue exitosa
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "par": pair,
                    "decision": decision,
                    "adx_valor": indicadores.get('adx_actual', 0),
                    "volatilidad_valor": indicadores.get('volatilidad_actual', 0),
                    "sentiment_promedio": indicadores.get('sentiment_promedio', 0),
                    "timestamp": datetime.now().isoformat(),
                    "razon": razon,
                    "fuente": "cerebro"
                }
                
                response = await client.post(
                    f"{self.grid_service_url}/cerebro/decision",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"✅ Grid respondió: {result.get('message', 'OK')}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Grid respondió con error {response.status_code}: {response.text}")
                    return False
                    
        except httpx.ConnectError:
            self.logger.warning(f"⚠️ Grid service no disponible en {self.grid_service_url}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error comunicándose con Grid API: {e}")
            return False
    
    async def notify_all_decisions(self, decisions: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Notifica todas las decisiones de una vez.
        
        Args:
            decisions: Diccionario con decisiones por par
                {
                    'ETH/USDT': {'decision': 'OPERAR_GRID', 'razon': '...', 'indicadores': {...}},
                    'BTC/USDT': {'decision': 'PAUSAR_GRID', 'razon': '...', 'indicadores': {...}},
                    ...
                }
        
        Returns:
            Diccionario con resultados por par
        """
        results = {}
        
        for pair, decision_data in decisions.items():
            try:
                success = await self.notify_grid_decision_change(
                    pair=pair,
                    decision=decision_data['decision'],
                    razon=decision_data['razon'],
                    indicadores=decision_data['indicadores']
                )
                results[pair] = success
                
            except Exception as e:
                self.logger.error(f"❌ Error notificando {pair}: {e}")
                results[pair] = False
        
        return results
    
    def get_grid_status_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del estado actual de todas las configuraciones del grid.
        
        Returns:
            Resumen del estado del grid
        """
        try:
            with get_db_session() as db:
                # Obtener todas las configuraciones activas
                active_configs = db.query(GridBotConfig).filter(
                    GridBotConfig.is_active == True,
                    GridBotConfig.is_configured == True
                ).all()
                
                summary = {
                    'total_configs': len(active_configs),
                    'pairs': {},
                    'decisions_summary': {
                        'OPERAR_GRID': 0,
                        'PAUSAR_GRID': 0,
                        'NO_DECISION': 0
                    }
                }
                
                for config in active_configs:
                    pair = config.pair
                    decision = getattr(config, 'last_decision', 'NO_DECISION')
                    is_running = getattr(config, 'is_running', False)
                    
                    summary['pairs'][pair] = {
                        'config_type': config.config_type,
                        'decision': decision,
                        'is_running': is_running,
                        'total_capital': config.total_capital,
                        'last_decision_timestamp': getattr(config, 'last_decision_timestamp', None)
                    }
                    
                    summary['decisions_summary'][decision] += 1
                
                return summary
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo resumen del grid: {e}")
            return {
                'error': str(e),
                'total_configs': 0,
                'pairs': {},
                'decisions_summary': {}
            }


# Instancia global del notificador
_multibot_notifier = None  # type: ignore

def get_multibot_notifier() -> MultibotNotifier:
    """Obtiene la instancia global del notificador multibot"""
    global _multibot_notifier
    if _multibot_notifier is None:
        _multibot_notifier = MultibotNotifier()
    return _multibot_notifier

def notify_decision_change(pair: str, decision: str, razon: str, indicadores: Dict[str, Any]) -> bool:
    """
    Función de conveniencia para notificar un cambio de decisión.
    
    Args:
        pair: Par de trading
        decision: Nueva decisión
        razon: Razón de la decisión
        indicadores: Indicadores utilizados
        
    Returns:
        True si la notificación fue exitosa
    """
    notifier = get_multibot_notifier()
    
    # Crear un event loop si no existe
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si el loop está corriendo, usar create_task
            task = loop.create_task(
                notifier.notify_grid_decision_change(pair, decision, razon, indicadores)
            )
            return True  # Asumimos éxito
        else:
            # Si el loop no está corriendo, ejecutar directamente
            return loop.run_until_complete(
                notifier.notify_grid_decision_change(pair, decision, razon, indicadores)
            )
    except RuntimeError:
        # No hay event loop, crear uno nuevo
        return asyncio.run(
            notifier.notify_grid_decision_change(pair, decision, razon, indicadores)
        )


__all__ = [
    'MultibotNotifier',
    'get_multibot_notifier',
    'notify_decision_change'
] 