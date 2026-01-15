"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Database
    DB_HOST: str = "localhost"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "heritage_routes"
    DB_PORT: int = 3306
    
    # JWT
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Application
    APP_NAME: str = "Heritage Routes System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001

    # Yandex
    YANDEX_GEOCODER_API_KEY: str = "fd1a272a-0331-44ed-8ffb-693497615815"
    
    # Route settings
    MAX_ROUTE_OBJECTS: int = 20  # Максимальное количество объектов в маршруте
    DEFAULT_ROUTE_OBJECTS: int = 5  # По умолчанию объектов в маршруте
    MAX_SEARCH_RADIUS_KM: int = 5  # Максимальный радиус поиска объектов (км)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()

