# Compatibilidad hacia atrás: importar desde shared
# TODO: Remover este archivo una vez completada la migración
from shared.config.settings import settings, Settings

# Re-exportar para compatibilidad
__all__ = ['Settings', 'settings'] 