#!/usr/bin/env python3
"""
Punto de entrada específico para el servicio de Grid Trading
Utiliza la nueva arquitectura modularizada en services/grid/
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config.settings import settings

if __name__ == "__main__":
    import uvicorn
    
    print("🤖 Iniciando Servicio de Grid Trading (Nueva Arquitectura)...")
    print("📍 Puerto: 8001")
    
    uvicorn.run(
        "services.grid.main:app",
        host="0.0.0.0",
        port=8001,  # Puerto diferente para el grid service
        reload=False,
        log_level="info"
    ) 