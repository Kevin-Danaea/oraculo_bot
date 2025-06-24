#!/usr/bin/env python3
"""
Script de Migración - Añadir campos de análisis enriquecido
============================================================

Este script añade las nuevas columnas primary_emotion y news_category 
a la tabla 'noticias' existente para soportar el análisis enriquecido.

Uso:
    python migrate_news_fields.py

Características:
- Idempotente: No falla si las columnas ya existen
- Compatible con SQLite y PostgreSQL
- Logging detallado del proceso
- Verificación de integridad post-migración

NOTA: Este script es temporal y puede eliminarse después de ejecutar
la migración en todos los entornos (desarrollo y VPS).
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database.session import SessionLocal, engine
from shared.services.logging_config import setup_logging, get_logger

# Configurar logging
setup_logging()
logger = get_logger(__name__)

def check_column_exists(table_name: str, column_name: str) -> bool:
    """
    Verifica si una columna existe en una tabla.
    
    Args:
        table_name: Nombre de la tabla
        column_name: Nombre de la columna
        
    Returns:
        bool: True si la columna existe, False si no existe
    """
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        return column_name in column_names
    except Exception as e:
        logger.error(f"Error verificando existencia de columna {column_name}: {e}")
        return False

def add_column_if_not_exists(table_name: str, column_name: str, column_type: str) -> bool:
    """
    Añade una columna a una tabla si no existe.
    
    Args:
        table_name: Nombre de la tabla
        column_name: Nombre de la columna
        column_type: Tipo de la columna (ej: 'TEXT')
        
    Returns:
        bool: True si se añadió o ya existía, False si hubo error
    """
    try:
        if check_column_exists(table_name, column_name):
            logger.info(f"✅ La columna '{column_name}' ya existe en la tabla '{table_name}'")
            return True
        
        # Construir el comando ALTER TABLE
        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        
        with engine.connect() as connection:
            connection.execute(text(alter_query))
            connection.commit()
            
        logger.info(f"✅ Columna '{column_name}' añadida exitosamente a la tabla '{table_name}'")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Error de base de datos al añadir columna '{column_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado al añadir columna '{column_name}': {e}")
        return False

def verify_migration() -> bool:
    """
    Verifica que la migración se completó correctamente.
    
    Returns:
        bool: True si todas las columnas están presentes
    """
    try:
        required_columns = ['primary_emotion', 'news_category']
        
        for column_name in required_columns:
            if not check_column_exists('noticias', column_name):
                logger.error(f"❌ Verificación fallida: La columna '{column_name}' no existe")
                return False
        
        logger.info("✅ Verificación completada: Todas las columnas nuevas están presentes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la verificación: {e}")
        return False

def get_table_info():
    """
    Muestra información de la tabla noticias para debug.
    """
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('noticias')
        
        logger.info("📋 Estructura actual de la tabla 'noticias':")
        for col in columns:
            logger.info(f"   - {col['name']}: {col['type']} (nullable: {col['nullable']})")
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo información de la tabla: {e}")

def drop_column_if_exists(table_name: str, column_name: str) -> bool:
    """
    Elimina una columna de una tabla si existe.
    
    Args:
        table_name: Nombre de la tabla
        column_name: Nombre de la columna a eliminar
        
    Returns:
        bool: True si se eliminó o no existía, False si hubo error
    """
    try:
        if not check_column_exists(table_name, column_name):
            logger.info(f"✅ La columna '{column_name}' no existe en la tabla '{table_name}' (ya limpia)")
            return True
        
        # Construir el comando ALTER TABLE DROP COLUMN
        # Nota: SQLite no soporta DROP COLUMN directamente, pero lo intentamos
        drop_query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
        
        with engine.connect() as connection:
            try:
                connection.execute(text(drop_query))
                connection.commit()
                logger.info(f"✅ Columna '{column_name}' eliminada exitosamente de la tabla '{table_name}'")
                return True
            except Exception as e:
                # SQLite no soporta DROP COLUMN, intentar método alternativo
                if "SQLite" in str(engine.url) or "sqlite" in str(e).lower():
                    logger.warning(f"⚠️ SQLite no soporta DROP COLUMN directamente para '{column_name}'")
                    logger.info(f"ℹ️ La columna '{column_name}' permanecerá en la tabla pero no se usará")
                    return True
                else:
                    raise e
            
    except SQLAlchemyError as e:
        logger.error(f"❌ Error de base de datos al eliminar columna '{column_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado al eliminar columna '{column_name}': {e}")
        return False

def run_migration():
    """
    Ejecuta la migración completa.
    """
    logger.info("🚀 Iniciando migración de campos de análisis enriquecido...")
    logger.info("=" * 60)
    
    # Mostrar estructura actual
    get_table_info()
    logger.info("-" * 60)
    
    # Lista de columnas a añadir
    columns_to_add = [
        ('primary_emotion', 'TEXT'),  # Emoción principal: Euforia, Optimismo, etc.
        ('news_category', 'TEXT')     # Categoría: Regulación, Tecnología/Adopción, etc.
    ]
    
    # Lista de columnas a eliminar (no utilizadas)
    columns_to_drop = ['entities']
    
    success = True
    
    # Paso 1: Añadir nuevas columnas
    logger.info("📥 PASO 1: Añadiendo nuevas columnas...")
    for column_name, column_type in columns_to_add:
        logger.info(f"🔄 Procesando columna '{column_name}'...")
        if not add_column_if_not_exists('noticias', column_name, column_type):
            success = False
            break
    
    # Paso 2: Eliminar columnas no utilizadas
    if success:
        logger.info("-" * 40)
        logger.info("🗑️ PASO 2: Eliminando columnas no utilizadas...")
        for column_name in columns_to_drop:
            logger.info(f"🔄 Eliminando columna '{column_name}'...")
            if not drop_column_if_exists('noticias', column_name):
                # No fallar la migración si no se puede eliminar la columna
                logger.warning(f"⚠️ No se pudo eliminar la columna '{column_name}', pero continuamos")
    
    if success:
        logger.info("-" * 60)
        logger.info("🔍 Verificando migración...")
        if verify_migration():
            logger.info("=" * 60)
            logger.info("🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
            logger.info("✅ Las nuevas columnas están listas para el análisis enriquecido")
            logger.info("🗑️ Columnas no utilizadas eliminadas (cuando es posible)")
            logger.info("💡 Ahora el servicio de news puede guardar:")
            logger.info("   - sentiment_score (float): Puntuación de sentimiento")
            logger.info("   - primary_emotion (str): Emoción dominante") 
            logger.info("   - news_category (str): Categoría de la noticia")
            logger.info("=" * 60)
            return True
        else:
            logger.error("❌ La verificación falló")
            return False
    else:
        logger.error("❌ La migración falló")
        return False

def main():
    """
    Función principal del script de migración.
    """
    try:
        logger.info("🔧 Script de Migración - Análisis Enriquecido de Noticias")
        logger.info(f"🗄️ Base de datos: {engine.url}")
        
        # Ejecutar migración
        success = run_migration()
        
        if success:
            logger.info("\n📝 PRÓXIMOS PASOS:")
            logger.info("1. Reiniciar el servicio de news para aplicar los cambios")
            logger.info("2. Verificar que el análisis enriquecido funcione correctamente")
            logger.info("3. Eliminar este script después de ejecutarlo en todos los entornos")
            sys.exit(0)
        else:
            logger.error("\n💥 LA MIGRACIÓN FALLÓ")
            logger.error("Revisa los logs para más detalles")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Migración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 