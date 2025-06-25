"""
Configuración compartida entre todos los microservicios.
Centraliza todas las variables de entorno y configuraciones.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra='ignore'  # Ignorar campos extra del .env
    )
    
    PROJECT_NAME: str = "Oráculo Cripto Bot"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./oraculo.db"  # Fallback por defecto
    
    # Configuración de Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "OraculoBot by mi_usuario_de_reddit"
    
    # API Key para Google Gemini
    GOOGLE_API_KEY: str = ""
    
    # Configuración para Grid Bot
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    
    # Configuración para notificaciones de Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

# Instancia global compartida
settings = Settings() 