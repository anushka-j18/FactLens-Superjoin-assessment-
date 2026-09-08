import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "FactLens API"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./factlens.db"
    
    # Providers
    LLM_PROVIDER: str = "mock"
    EMBEDDING_PROVIDER: str = "mock"
    
    # API Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
