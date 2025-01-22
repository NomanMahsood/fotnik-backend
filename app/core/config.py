from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Fotnik API"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]
    
    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fotnik"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 