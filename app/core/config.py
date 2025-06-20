from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Oráculo Cripto Bot"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./oraculo.db"
    
    # URL de la API de CryptoPanic
    CRYPTOPANIC_API_URL: str = "https://cryptopanic.com/api/developer/v2/posts/"
    # API Key para CryptoPanic
    CRYPTOPANIC_API_KEY: str = ""
    # API Key para Google Gemini
    GOOGLE_API_KEY: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 