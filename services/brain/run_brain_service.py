#!/usr/bin/env python3
"""
Script de Ejecución del Brain Service
=====================================

Script para ejecutar el brain service en modo desarrollo.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Agregar el directorio raíz al path para importar shared
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Función principal para ejecutar el brain service."""
    
    # Configurar variables de entorno por defecto si no están definidas
    os.environ.setdefault('BRAIN_ANALYSIS_INTERVAL', '3600')
    os.environ.setdefault('BRAIN_ANALYSIS_TIMEFRAME', '4h')
    os.environ.setdefault('BRAIN_ANALYSIS_DAYS', '40')
    os.environ.setdefault('BRAIN_LOG_LEVEL', 'INFO')
    os.environ.setdefault('BRAIN_DEBUG', 'true')
    os.environ.setdefault('BRAIN_DEV_MODE', 'true')
    
    # Configurar logging
    os.environ.setdefault('BRAIN_LOG_FILE', 'logs/brain_service.log')
    
    # Crear directorio de logs si no existe
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    print("🧠 Iniciando Brain Service...")
    print("📋 Configuración:")
    print(f"   🔧 Debug: {os.getenv('BRAIN_DEBUG', 'false')}")
    print(f"   🔧 Dev Mode: {os.getenv('BRAIN_DEV_MODE', 'false')}")
    print(f"   📊 Log Level: {os.getenv('BRAIN_LOG_LEVEL', 'INFO')}")
    print(f"   ⏰ Analysis Interval: {os.getenv('BRAIN_ANALYSIS_INTERVAL', '3600')}s")
    print(f"   📁 Log File: {os.getenv('BRAIN_LOG_FILE', 'logs/brain_service.log')}")
    
    # Ejecutar el servicio
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main() 