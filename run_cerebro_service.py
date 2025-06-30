#!/usr/bin/env python3
"""
Punto de entrada específico para el Servicio Cerebro
Motor de Decisiones de Trading con Análisis Continuo
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config.settings import settings

if __name__ == "__main__":
    import uvicorn
    
    print("🧠 ============================================================")
    print("🧠 SERVICIO CEREBRO - MOTOR DE DECISIONES v2.0")
    print("🧠 ============================================================")
    print("📍 Puerto: 8004")
    print("🔄 Análisis continuo activado")
    print("📊 Pares monitoreados: ETH/USDT")
    print("⏰ Intervalo: cada 2 horas")
    print("💾 Base de datos: tabla estrategia_status")
    print("🔄 Iniciando servidor...")
    print("")
    
    uvicorn.run(
        "services.cerebro.main:app",
        host="0.0.0.0",
        port=8004,  # Puerto específico para el cerebro service
        reload=False,
        log_level="info",
        access_log=True
    ) 