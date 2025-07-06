"""
Base común para todos los modelos de SQLAlchemy.
Define la declarative_base que deben usar todos los modelos.
"""
from sqlalchemy.ext.declarative import declarative_base

# Base común para todos los modelos del sistema
Base = declarative_base() 