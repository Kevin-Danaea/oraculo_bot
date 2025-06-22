# DEPRECATED: CryptoPanic service ha sido completamente removido
# TODO: Remover este archivo una vez completada la migración
# Fue reemplazado por Reddit r/CryptoCurrency que es más confiable

def fetch_and_store_posts(db):
    """
    CryptoPanic service fue reemplazado por Reddit r/CryptoCurrency.
    Esta función es mantenida solo para compatibilidad legacy.
    """
    return {
        "success": False,
        "error": "CryptoPanic service ha sido DEPRECATED y removido. Usar Reddit r/CryptoCurrency en su lugar.",
        "message": "Servicio obsoleto - usar Reddit"
    }

# Re-exportar para compatibilidad (aunque retorna error)
__all__ = ['fetch_and_store_posts'] 