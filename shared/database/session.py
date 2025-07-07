"""
Sesión de base de datos compartida entre todos los microservicios.
Proporciona acceso consistente a la BD SQLite compartida.
"""
import time
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError
from shared.config.settings import settings

logger = logging.getLogger(__name__)

def create_engine_with_ssl_config():
    """
    Crea un engine de SQLAlchemy con configuración SSL optimizada para PostgreSQL.
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        # Configuración específica para SQLite
        return create_engine(
            settings.DATABASE_URL, 
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            pool_recycle=3600
        )
    else:
        # Configuración optimizada para PostgreSQL con SSL
        connect_args = {}
        
        # Configuración SSL para PostgreSQL
        if "postgresql" in settings.DATABASE_URL.lower():
            connect_args.update({
                "sslmode": "require",  # Requerir SSL
                "connect_timeout": 10,  # Timeout de conexión
                "application_name": "oraculo_bot",  # Identificador de aplicación
                "keepalives_idle": 30,  # Keepalive cada 30 segundos
                "keepalives_interval": 10,  # Intervalo de keepalive
                "keepalives_count": 5,  # Número de keepalives antes de cerrar
            })
        
        return create_engine(
            settings.DATABASE_URL,
            pool_size=5,  # Reducido para evitar sobrecarga
            max_overflow=10,  # Reducido para evitar sobrecarga
            pool_recycle=1800,  # Reciclar conexiones cada 30 minutos
            pool_pre_ping=True,  # Verificar conexión antes de usar
            pool_timeout=30,  # Timeout para obtener conexión del pool
            connect_args=connect_args,
            echo=False  # Desactivar logging SQL para producción
        )

# Crear el engine con configuración optimizada
engine = create_engine_with_ssl_config()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configurar eventos para manejar reconexiones
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configurar SQLite para mejor rendimiento."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Verificar conexión al obtener del pool."""
    try:
        # Ejecutar una consulta simple para verificar la conexión
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except Exception as e:
        logger.warning(f"⚠️ Conexión corrupta detectada, será reciclada: {e}")
        raise DisconnectionError("Conexión corrupta detectada")

def get_db_with_retry(max_retries=3, retry_delay=1):
    """
    Obtiene una sesión de base de datos con reintentos automáticos.
    
    Args:
        max_retries: Número máximo de reintentos
        retry_delay: Delay entre reintentos en segundos
    
    Returns:
        Session: Sesión de base de datos válida
    """
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Verificar que la conexión funciona
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            return db
        except (OperationalError, DisconnectionError) as e:
            logger.warning(f"⚠️ Intento {attempt + 1}/{max_retries} falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Backoff exponencial
                continue
            else:
                logger.error(f"❌ No se pudo establecer conexión después de {max_retries} intentos")
                raise
        except Exception as e:
            logger.error(f"❌ Error inesperado al conectar a la BD: {e}")
            raise

def init_database():
    """
    Inicializa la base de datos creando todas las tablas definidas en los modelos.
    Esta función debe ser llamada al iniciar cada servicio para asegurar que las tablas existan.
    """
    try:
        from shared.database.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        raise

def get_db():
    """
    Dependencia para obtener una sesión de base de datos.
    Útil para FastAPI dependency injection.
    """
    db = None
    try:
        db = get_db_with_retry()
        yield db
    except Exception as e:
        logger.error(f"❌ Error en get_db: {e}")
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando sesión de BD: {e}")

@contextmanager
def get_db_session():
    """
    Context manager para obtener una sesión de base de datos con manejo de errores.
    Útil para operaciones directas fuera de FastAPI.
    """
    db = None
    try:
        db = get_db_with_retry()
        yield db
    except Exception as e:
        logger.error(f"❌ Error en get_db_session: {e}")
        if db:
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.warning(f"⚠️ Error en rollback: {rollback_error}")
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando sesión de BD: {e}")

def health_check():
    """
    Verifica la salud de la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión está saludable, False en caso contrario
    """
    try:
        with get_db_session() as db:
            if db is None:
                logger.error("❌ No se pudo obtener sesión de base de datos")
                return False
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"❌ Health check falló: {e}")
        return False 