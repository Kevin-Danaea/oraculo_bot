# Compatibilidad hacia atrás: importar desde shared
# TODO: Remover este archivo una vez completada la migración
from shared.services.logging_config import setup_logging, get_logger

# Re-exportar para compatibilidad
__all__ = ['setup_logging', 'get_logger'] 