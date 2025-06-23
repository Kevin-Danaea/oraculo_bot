"""
Sesión de base de datos compartida entre todos los microservicios.
Proporciona acceso consistente a la BD SQLite compartida.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.config.settings import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_database():
    """
    Inicializa la base de datos creando todas las tablas definidas en los modelos.
    Esta función debe ser llamada al iniciar cada servicio para asegurar que las tablas existan.
    """
    from shared.database.models import Base
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependencia para obtener una sesión de base de datos.
    Útil para FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 