"""
Configuración del Servicio Cerebro
=================================

Configuración centralizada para el servicio cerebro con parámetros
óptimos obtenidos de backtesting.

NUEVA ARQUITECTURA PROACTIVA:
- El cerebro monitorea continuamente y NOTIFICA al Grid
- Grid consulta estado inicial al arrancar  
- Cerebro detecta cambios y comunica automáticamente
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================================
# CONFIGURACIÓN ÓPTIMA OBTENIDA DE BACKTESTING
# ============================================================================

CONFIGURACIONES_OPTIMAS: Dict[str, Dict[str, Any]] = {
    "ETH/USDT": {
        "UMBRAL_ADX": 30,                    # ADX debe ser menor a 30
        "UMBRAL_VOLATILIDAD": 0.035,         # Ancho de Banda de Bollinger debe ser mayor a 0.035
        "UMBRAL_SENTIMIENTO": -0.20,         # Media Móvil de Sentimiento (7d) debe ser mayor a -0.20
        "GRID_RANGO": 10.0,                  # Rango de precios: 10.0%
        "GRID_NIVELES": 30                   # Niveles de grid: 30
    }
}

# ============================================================================
# LISTA DE PARES A MONITOREAR
# ============================================================================

PARES_A_MONITOREAR: List[str] = ['ETH/USDT']

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

# URL de base de datos desde .env
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada en el archivo .env")

# ============================================================================
# CONFIGURACIÓN DE ANÁLISIS
# ============================================================================

# Parámetros para recolección de datos
TIMEFRAME = '4h'
DIAS_HISTORIAL = 40

# Intervalo del bucle principal (en segundos) - 2 horas
INTERVALO_ANALISIS = 7200

# Configuración de logging
LOG_LEVEL = "INFO" 