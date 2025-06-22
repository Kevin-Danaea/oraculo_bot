"""
Sesión de base de datos compartida entre todos los microservicios.
Proporciona acceso consistente a la BD SQLite compartida.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.config.settings import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 