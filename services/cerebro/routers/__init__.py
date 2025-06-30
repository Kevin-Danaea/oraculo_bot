"""
Routers del Servicio Cerebro
===========================

Módulo que contiene todos los routers del servicio cerebro.
"""

from .health_router import router as health_router

__all__ = ["health_router"] 