from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # FastAPI
    PROJECT_NAME: str = "English Learning API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "1234")  
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "english_learning")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    @property
    def DATABASE_URL(self) -> str:
        # Используем pg8000 
        return f"postgresql+pg8000://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "fallback-refresh-secret-key-change-in-production")
    
    class Config:
        env_file = ".env"

settings = Settings()