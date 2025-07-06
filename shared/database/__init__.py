"""
Módulo de base de datos compartida entre todos los microservicios.
"""
from .session import SessionLocal, init_database, get_db
from . import models

# Mantener compatibilidad con imports directos del modelo anterior
from .models import Base, Noticia, GridBotConfig, GridBotState, HypeEvent, EstrategiaStatus, HypeScan, HypeMention

__all__ = ['SessionLocal', 'init_database', 'get_db', 'models', 'Base', 
           'Noticia', 'GridBotConfig', 'GridBotState', 'HypeEvent', 'EstrategiaStatus', 'HypeScan', 'HypeMention'] 