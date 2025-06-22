"""
Routers del API Gateway.
Exporta el status_router para monitoreo y health checks de workers.
"""

from . import status_router

__all__ = ['status_router'] 