# Compatibilidad hacia atrás: importar desde shared
# TODO: Remover este archivo una vez completada la migración
from shared.database.models import Base, Noticia

# Re-exportar para compatibilidad
__all__ = ['Base', 'Noticia'] 