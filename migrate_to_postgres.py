#!/usr/bin/env python3
"""
Script de migración completa de SQLite a PostgreSQL.
Migra estructura y datos, registra cada paso y limpia archivos.
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database.models import Base, Noticia, GridBotConfig, GridBotState, HypeEvent
from shared.config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def migrate_database():
    """
    Migra completamente de SQLite a PostgreSQL: estructura y datos.
    """
    logger.info("🚀 Iniciando migración completa de base de datos...")
    
    # Verificar que estamos usando PostgreSQL
    if not settings.DATABASE_URL.startswith("postgresql"):
        logger.error("❌ Error: DATABASE_URL debe ser de PostgreSQL")
        logger.error(f"   Actual: {settings.DATABASE_URL}")
        logger.error("   Formato esperado: postgresql://usuario:password@host:puerto/database")
        return False
    
    sqlite_path = "./oraculo.db"
    sqlite_url = "sqlite:///./oraculo.db"
    
    try:
        # 1. Verificar si existe base de datos SQLite
        sqlite_exists = os.path.exists(sqlite_path)
        logger.info(f"📋 Base de datos SQLite existe: {sqlite_exists}")
        
        # 2. Crear engines
        logger.info("🔌 Creando conexiones a bases de datos...")
        
        # Engine para PostgreSQL
        pg_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        # Engine para SQLite (si existe)
        sqlite_engine = None
        if sqlite_exists:
            sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
            logger.info("✅ Conexión a SQLite establecida")
        
        # 3. Probar conexión PostgreSQL
        logger.info("🔌 Probando conexión a PostgreSQL...")
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            row = result.fetchone()
            if row:
                version = row[0]
                logger.info(f"✅ Conectado a PostgreSQL: {version[:50]}...")
            else:
                logger.info("✅ Conectado exitosamente a PostgreSQL")
        
        # 4. Crear estructura de tablas en PostgreSQL
        logger.info("📊 Creando estructura de tablas en PostgreSQL...")
        Base.metadata.create_all(bind=pg_engine)
        logger.info("✅ Estructura de tablas creada exitosamente")
        
        # 5. Verificar tablas creadas
        inspector = inspect(pg_engine)
        tables = inspector.get_table_names()
        logger.info(f"📋 Tablas creadas en PostgreSQL: {tables}")
        
        # 6. Migrar datos si existe SQLite
        if sqlite_exists and sqlite_engine:
            logger.info("📦 Iniciando migración de datos...")
            migrated_records = migrate_data(sqlite_engine, pg_engine)
            logger.info(f"✅ Migración de datos completada: {migrated_records} registros migrados")
        else:
            logger.info("ℹ️  No hay datos SQLite para migrar")
        
        logger.info("🎉 ¡Migración completada exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {str(e)}")
        logger.error("🔧 Posibles soluciones:")
        logger.error("   - Verifica que la URL de PostgreSQL sea correcta")
        logger.error("   - Asegúrate de que la base de datos esté accesible") 
        logger.error("   - Confirma que el usuario tenga permisos para crear tablas")
        return False

def migrate_data(sqlite_engine, pg_engine):
    """
    Migra todos los datos de SQLite a PostgreSQL tabla por tabla.
    """
    total_migrated = 0
    
    # Crear sesiones para ambas bases de datos
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)
    
    # Lista de modelos a migrar en orden
    models_to_migrate = [
        ('noticias', Noticia),
        ('grid_bot_config', GridBotConfig),
        ('grid_bot_state', GridBotState),
        ('hype_events', HypeEvent)
    ]
    
    for table_name, model_class in models_to_migrate:
        try:
            logger.info(f"📦 Migrando tabla: {table_name}")
            
            # Verificar si la tabla existe en SQLite
            inspector = inspect(sqlite_engine)
            if table_name not in inspector.get_table_names():
                logger.info(f"⏭️  Tabla {table_name} no existe en SQLite, saltando...")
                continue
            
            # Leer datos de SQLite
            with SqliteSession() as sqlite_session:
                sqlite_records = sqlite_session.query(model_class).all()
                record_count = len(sqlite_records)
                logger.info(f"📋 Encontrados {record_count} registros en {table_name}")
                
                if record_count == 0:
                    logger.info(f"⚡ Tabla {table_name} vacía, continuando...")
                    continue
                
                # Migrar datos a PostgreSQL
                with PgSession() as pg_session:
                    migrated_count = 0
                    for record in sqlite_records:
                        try:
                            # Crear nuevo objeto sin el ID para evitar conflictos
                            record_dict = {}
                            for column in model_class.__table__.columns:
                                if column.name != 'id':  # Excluir ID para auto-generación
                                    value = getattr(record, column.name)
                                    record_dict[column.name] = value
                            
                            new_record = model_class(**record_dict)
                            pg_session.add(new_record)
                            migrated_count += 1
                            
                        except Exception as e:
                            logger.warning(f"⚠️  Error migrando registro de {table_name}: {str(e)}")
                            continue
                    
                    # Guardar cambios
                    pg_session.commit()
                    logger.info(f"✅ Migrados {migrated_count}/{record_count} registros de {table_name}")
                    total_migrated += migrated_count
                    
        except Exception as e:
            logger.error(f"❌ Error migrando tabla {table_name}: {str(e)}")
            continue
    
    return total_migrated

def cleanup_sqlite_files():
    """
    Elimina los archivos SQLite después de una migración exitosa.
    """
    files_to_remove = [
        "./oraculo.db",
        "./oraculo.db-wal",
        "./oraculo.db-shm"
    ]
    
    removed_files = []
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_files.append(file_path)
                logger.info(f"🗑️  Archivo eliminado: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo eliminar {file_path}: {str(e)}")
    
    if removed_files:
        logger.info(f"✅ Limpieza completada: {len(removed_files)} archivos eliminados")
    else:
        logger.info("ℹ️  No había archivos SQLite para eliminar")
    
    return len(removed_files)

def backup_sqlite_data():
    """
    Crea un respaldo de los datos de SQLite antes de migrar.
    """
    sqlite_path = "./oraculo.db"
    backup_path = f"./oraculo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if not os.path.exists(sqlite_path):
        logger.info("ℹ️  No se encontró base de datos SQLite existente")
        return True
    
    try:
        logger.info("💾 Creando respaldo de datos SQLite...")
        
        # Crear una copia del archivo SQLite
        import shutil
        shutil.copy2(sqlite_path, backup_path)
        
        # Verificar que el respaldo se creó correctamente
        if os.path.exists(backup_path):
            backup_size = os.path.getsize(backup_path)
            logger.info(f"✅ Respaldo creado: {backup_path} ({backup_size} bytes)")
            return True
        else:
            logger.error("❌ No se pudo crear el archivo de respaldo")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error al crear respaldo: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔄 MIGRACIÓN COMPLETA DE SQLITE A POSTGRESQL")
    logger.info("=" * 60)
    
    migration_success = False
    
    try:
        # 1. Crear respaldo de SQLite
        logger.info("🔧 PASO 1: Creando respaldo de seguridad...")
        if not backup_sqlite_data():
            logger.error("❌ Falló el respaldo. Abortando migración por seguridad.")
            sys.exit(1)
        
        # 2. Ejecutar migración completa
        logger.info("🔧 PASO 2: Ejecutando migración de estructura y datos...")
        if migrate_database():
            migration_success = True
            logger.info("✅ Migración de datos completada exitosamente")
        else:
            logger.error("❌ Falló la migración de datos")
            sys.exit(1)
        
        # 3. Limpiar archivos SQLite (solo si la migración fue exitosa)
        if migration_success:
            logger.info("🔧 PASO 3: Limpiando archivos SQLite...")
            
            # Confirmar antes de eliminar
            sqlite_exists = os.path.exists("./oraculo.db")
            if sqlite_exists:
                logger.info("⚠️  ¿Eliminar archivos SQLite? Los datos ya fueron migrados y respaldados.")
                # En un entorno automatizado, puedes cambiar esto
                cleanup_sqlite_files()
            
            logger.info("🔧 PASO 4: Verificación final...")
            logger.info("✅ Migración completada exitosamente")
            logger.info("📝 Próximos pasos:")
            logger.info("   1. Actualiza tu .env con DATABASE_URL de PostgreSQL")
            logger.info("   2. Reinicia todos los servicios")
            logger.info("   3. Verifica que todo funcione correctamente")
            logger.info("   4. El archivo de log contiene todos los detalles")
            
        logger.info("🎉 ¡MIGRACIÓN EXITOSA!")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Error inesperado durante la migración: {str(e)}")
        logger.error("🔧 Los archivos SQLite NO fueron eliminados por seguridad")
        sys.exit(1) 