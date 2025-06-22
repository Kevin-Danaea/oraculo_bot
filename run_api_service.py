#!/usr/bin/env python3
"""
Punto de entrada específico para el API Gateway
Centraliza todos los endpoints de los microservicios de Oráculo Bot.
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    
    print("🌐 Iniciando API Gateway...")
    print("🚀 Centralizando endpoints de microservicios")
    
    uvicorn.run(
        "services.api.main:app",
        host="0.0.0.0",
        port=8002,  # Puerto específico para API Gateway
        reload=False,
        log_level="info"
    ) 