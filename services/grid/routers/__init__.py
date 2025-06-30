"""
Routers para el servicio Grid Trading
"""

from .health_router import router as health_router
from .cerebro_router import router as cerebro_router
from .config_router import router as config_router

__all__ = ['health_router', 'cerebro_router', 'config_router'] 