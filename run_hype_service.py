#!/usr/bin/env python3
"""
Punto de entrada específico para el servicio de Hype Radar
Utiliza la nueva arquitectura modularizada en services/hype/
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config.settings import settings

if __name__ == "__main__":
    import uvicorn
    
    print("🎯 Iniciando Servicio de Hype Radar (Nueva Arquitectura)...")
    print("📍 Puerto: 8003")
    
    uvicorn.run(
        "services.hype.main:app",
        host="0.0.0.0",
        port=8003,  # Puerto diferente para el hype service
        reload=False,
        log_level="info"
    ) 