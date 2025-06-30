"""
Motor de Decisiones del Servicio Cerebro
=======================================

Motor que toma decisiones de trading basadas en análisis técnico
según la lógica específica de ADX y volatilidad.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from .config import CONFIGURACIONES_OPTIMAS
from .data_collector import fetch_and_prepare_data, get_current_indicators
from shared.database.session import SessionLocal
from shared.database.models import EstrategiaStatus

logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    Motor de decisiones simplificado para trading grid.
    
    Lógica de decisión:
    - OPERAR_GRID: Solo si ADX < UMBRAL_ADX Y bb_width > UMBRAL_VOLATILIDAD
    - PAUSAR_GRID: Si cualquiera de las condiciones anteriores no se cumple
    """
    
    def __init__(self):
        """
        Inicializa el motor de decisiones.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("🧠 Motor de decisiones inicializado")
        
    def analizar_par(self, par: str) -> Dict[str, Any]:
        """
        Analiza un par específico y toma una decisión de trading.
        
        Args:
            par: Par de trading (ej: 'ETH/USDT')
            
        Returns:
            Diccionario con la decisión y detalles del análisis
        """
        try:
            logger.info(f"🔍 Analizando {par}...")
            
            # Verificar que el par esté configurado
            if par not in CONFIGURACIONES_OPTIMAS:
                raise ValueError(f"Par {par} no encontrado en la configuración")
            
            config = CONFIGURACIONES_OPTIMAS[par]
            
            # Obtener datos históricos y calcular indicadores
            logger.info(f"📊 Obteniendo datos históricos para {par}...")
            df = fetch_and_prepare_data(par, timeframe='4h', days=40)
            
            if df is None or df.empty:
                raise Exception(f"No se pudieron obtener datos para {par}")
            
            # Extraer indicadores actuales
            indicadores = get_current_indicators(df)
            
            if not indicadores:
                raise Exception(f"No se pudieron calcular indicadores para {par}")
            
            # Extraer valores y convertir tipos de NumPy a tipos nativos de Python
            adx_value = indicadores.get('adx_actual')
            volatilidad_value = indicadores.get('volatilidad_actual')
            sentiment_value = indicadores.get('sentiment_promedio')
            
            # Convertir a float nativo de Python solo si no es None
            adx_actual = float(adx_value) if adx_value is not None else None
            volatilidad_actual = float(volatilidad_value) if volatilidad_value is not None else None
            sentiment_promedio = float(sentiment_value) if sentiment_value is not None else None
            
            # Validar que los indicadores críticos no sean None
            if adx_actual is None or volatilidad_actual is None:
                raise Exception(f"Indicadores críticos faltantes para {par}: ADX={adx_actual}, Volatilidad={volatilidad_actual}")
            
            logger.info(f"📈 Indicadores calculados: ADX={adx_actual:.2f}, Volatilidad={volatilidad_actual:.4f}, Sentiment={sentiment_promedio:.3f}" if sentiment_promedio is not None else f"📈 Indicadores calculados: ADX={adx_actual:.2f}, Volatilidad={volatilidad_actual:.4f}, Sentiment=N/A")
            
            # Aplicar lógica de decisión
            decision = self._tomar_decision(
                adx_actual=adx_actual,
                volatilidad_actual=volatilidad_actual,
                config=config
            )
            
            # Generar razón de la decisión
            razon = self._generar_razon(
                decision=decision,
                adx_actual=adx_actual,
                volatilidad_actual=volatilidad_actual,
                config=config
            )
            
            logger.info(f"🎯 Decisión para {par}: {decision}")
            logger.info(f"📝 Razón: {razon}")
            
            # Actualizar estado en base de datos
            self._actualizar_estado_bd(
                par=par,
                decision=decision,
                razon=razon,
                adx_actual=adx_actual,
                volatilidad_actual=volatilidad_actual,
                sentiment_promedio=sentiment_promedio,
                config=config
            )
            
            return {
                "par": par,
                "decision": decision,
                "razon": razon,
                "indicadores": {
                    "adx_actual": adx_actual,
                    "volatilidad_actual": volatilidad_actual,
                    "sentiment_promedio": sentiment_promedio
                },
                "umbrales": config,
                "timestamp": datetime.now(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando {par}: {str(e)}")
            return {
                "par": par,
                "decision": "ERROR",
                "razon": f"Error en análisis: {str(e)}",
                "timestamp": datetime.now(),
                "success": False,
                "error": str(e)
            }
    
    def _tomar_decision(
        self, 
        adx_actual: float, 
        volatilidad_actual: float, 
        config: Dict[str, Any]
    ) -> str:
        """
        Aplica la lógica de decisión basada en los umbrales.
        
        Args:
            adx_actual: Valor actual del ADX
            volatilidad_actual: Valor actual de la volatilidad (bb_width)
            config: Configuración del par
            
        Returns:
            Decisión: 'OPERAR_GRID' o 'PAUSAR_GRID'
        """
        umbral_adx = config['UMBRAL_ADX']
        umbral_volatilidad = config['UMBRAL_VOLATILIDAD']
        
        # Lógica de decisión: AMBAS condiciones deben cumplirse
        condicion_adx = adx_actual < umbral_adx
        condicion_volatilidad = volatilidad_actual > umbral_volatilidad
        
        if condicion_adx and condicion_volatilidad:
            return "OPERAR_GRID"
        else:
            return "PAUSAR_GRID"
    
    def _generar_razon(
        self, 
        decision: str, 
        adx_actual: float, 
        volatilidad_actual: float, 
        config: Dict[str, Any]
    ) -> str:
        """
        Genera una explicación textual de la decisión tomada.
        
        Args:
            decision: Decisión tomada
            adx_actual: Valor actual del ADX
            volatilidad_actual: Valor actual de la volatilidad
            config: Configuración del par
            
        Returns:
            Razón textual de la decisión
        """
        umbral_adx = config['UMBRAL_ADX']
        umbral_volatilidad = config['UMBRAL_VOLATILIDAD']
        
        condicion_adx = adx_actual < umbral_adx
        condicion_volatilidad = volatilidad_actual > umbral_volatilidad
        
        if decision == "OPERAR_GRID":
            return f"ADX ({adx_actual:.1f}) < {umbral_adx} Y Volatilidad ({volatilidad_actual:.3f}) > {umbral_volatilidad}"
        else:
            razones = []
            if not condicion_adx:
                razones.append(f"ADX ({adx_actual:.1f}) >= {umbral_adx}")
            if not condicion_volatilidad:
                razones.append(f"Volatilidad ({volatilidad_actual:.3f}) <= {umbral_volatilidad}")
            
            return "Condiciones no cumplidas: " + " Y ".join(razones)
    
    def _actualizar_estado_bd(
        self,
        par: str,
        decision: str,
        razon: str,
        adx_actual: float,
        volatilidad_actual: float,
        sentiment_promedio: Optional[float],
        config: Dict[str, Any]
    ):
        """
        Actualiza o inserta el estado en la base de datos (upsert).
        
        Args:
            par: Par de trading
            decision: Decisión tomada
            razon: Razón de la decisión
            adx_actual: Valor actual del ADX
            volatilidad_actual: Valor actual de la volatilidad
            sentiment_promedio: Promedio de sentiment
            config: Configuración utilizada
        """
        db = SessionLocal()
        try:
            logger.info("💾 Actualizando estado en la base de datos...")
            
            # Buscar registro existente
            existing = db.query(EstrategiaStatus).filter(
                EstrategiaStatus.par == par,
                EstrategiaStatus.estrategia == 'GRID'
            ).first()
            
            timestamp_now = datetime.now()
            
            if existing:
                # Actualizar registro existente
                existing.decision = decision  # type: ignore
                existing.razon = razon  # type: ignore
                existing.adx_actual = adx_actual  # type: ignore
                existing.volatilidad_actual = volatilidad_actual  # type: ignore
                existing.sentiment_promedio = sentiment_promedio  # type: ignore
                existing.umbral_adx = config['UMBRAL_ADX']  # type: ignore
                existing.umbral_volatilidad = config['UMBRAL_VOLATILIDAD']  # type: ignore
                existing.timestamp = timestamp_now  # type: ignore
                existing.updated_at = timestamp_now  # type: ignore
                
                logger.info(f"✅ Estado actualizado para {par}")
            else:
                # Crear nuevo registro
                nuevo_estado = EstrategiaStatus(
                    par=par,
                    estrategia='GRID',
                    decision=decision,
                    razon=razon,
                    adx_actual=adx_actual,
                    volatilidad_actual=volatilidad_actual,
                    sentiment_promedio=sentiment_promedio,
                    umbral_adx=config['UMBRAL_ADX'],
                    umbral_volatilidad=config['UMBRAL_VOLATILIDAD'],
                    timestamp=timestamp_now
                )
                db.add(nuevo_estado)
                
                logger.info(f"✅ Nuevo estado creado para {par}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estado en BD: {e}")
            db.rollback()
            raise
        finally:
            db.close() 