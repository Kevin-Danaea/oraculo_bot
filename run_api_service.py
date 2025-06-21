#!/usr/bin/env python3
"""
Punto de entrada específico para solo la API (sin schedulers)
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

# Configurar el modo del servicio
os.environ["SERVICE_MODE"] = "api"

if __name__ == "__main__":
    import uvicorn
    
    print("🌐 Iniciando Servicio de API...")
    print(f"🔧 Modo: {os.environ.get('SERVICE_MODE', 'api')}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,  # Puerto diferente para la API
        reload=False,
        log_level="info"
    ) 