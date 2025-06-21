from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Oráculo Cripto Bot"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./oraculo.db"
    
    # URL de la API de CryptoPanic (Deprecated - usando Reddit ahora)
    CRYPTOPANIC_API_URL: str = "https://cryptopanic.com/api/developer/v2/posts/"
    # API Key para CryptoPanic (Deprecated - usando Reddit ahora)
    CRYPTOPANIC_API_KEY: str = ""
    
    # Configuración de Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "OraculoBot by mi_usuario_de_reddit"
    
    # API Key para Google Gemini
    GOOGLE_API_KEY: str = ""
    
    # Configuración de Microservicios
    SERVICE_MODE: str = "all"  # "all", "news", "grid", "api"
    
    # Configuración para Grid Bot
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    
    # Configuración para notificaciones de Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 