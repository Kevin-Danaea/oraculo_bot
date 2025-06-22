"""
Configuración de logging compartida entre todos los microservicios.
Proporciona logging consistente para toda la aplicación.
"""
import logging
import sys
from pathlib import Path

def setup_logging():
    """
    Configura el sistema de logging para toda la aplicación.
    Logs se mostrarán en consola y se guardarán en archivo.
    """
    # Crear directorio de logs si no existe
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configurar formato de logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configurar el logger root
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Handler para consola
            logging.StreamHandler(sys.stdout),
            # Handler para archivo
            logging.FileHandler(
                logs_dir / "oraculo_bot.log",
                mode='a',
                encoding='utf-8'
            )
        ]
    )
    
    # Configurar logger para la aplicación
    logger = logging.getLogger("oraculo_bot")
    logger.setLevel(logging.INFO)
    
    return logger

def get_logger(name: str):
    """
    Obtiene un logger con el nombre especificado.
    
    Args:
        name: Nombre del logger (generalmente __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(f"oraculo_bot.{name}") 