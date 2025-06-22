#!/usr/bin/env python3
"""
Punto de entrada específico para el servicio de noticias
Utiliza la nueva arquitectura modularizada en services/news/
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config.settings import settings

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Servicio de Noticias (Nueva Arquitectura)...")
    print("📍 Puerto: 8000")
    
    uvicorn.run(
        "services.news.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 