# Compatibilidad hacia atrás: importar desde shared
# TODO: Remover este archivo una vez completada la migración
from shared.database.session import engine, SessionLocal

# Re-exportar para compatibilidad
__all__ = ['engine', 'SessionLocal'] 