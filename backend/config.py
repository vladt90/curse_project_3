"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Database
    DB_HOST: str = "localhost"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "heritage_routes"
    DB_PORT: int = 3306
    
    # JWT

    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Application
    APP_NAME: str = "Heritage Routes System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Yandex
    YANDEX_GEOCODER_API_KEY: str = ""

    # LLM (OpenRouter)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemma-3n-e2b-it:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Route settings
    MAX_ROUTE_OBJECTS: int = 20  # Максимальное количество объектов в маршруте
    DEFAULT_ROUTE_OBJECTS: int = 5  # По умолчанию объектов в маршруте
    MAX_SEARCH_RADIUS_KM: int = 5  # Максимальный радиус поиска объектов (км)
    
    class Config:
        # Всегда читаем .env рядом с этим файлом (backend/.env),
        # независимо от того, из какой директории запускают приложение.
        env_file = str(Path(__file__).resolve().parent / ".env")
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()

