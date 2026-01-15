"""
Pydantic модели для валидации данных
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


# ============================================
# Модели пользователей
# ============================================

class UserCreate(BaseModel):
    """Модель для регистрации пользователя"""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Имя пользователя может содержать только буквы, цифры, _ и -')
        return v


class UserLogin(BaseModel):
    """Модель для входа пользователя"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Модель ответа с данными пользователя"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Модель токена авторизации"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================
# Модели объектов наследия
# ============================================

class HeritageObject(BaseModel):
    """Модель объекта культурного наследия"""
    id: int
    global_id: int
    name: str
    address: str
    district: Optional[str]
    adm_area: Optional[str]
    object_type: Optional[str]
    category: Optional[str]
    security_status: Optional[str]
    description: Optional[str]
    build_year: Optional[str]
    latitude: float
    longitude: float
    distance: Optional[float] = None  # Расстояние от точки старта (в метрах)
    
    class Config:
        from_attributes = True


class HeritageObjectList(BaseModel):
    """Список объектов с пагинацией"""
    objects: List[HeritageObject]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================
# Модели маршрутов
# ============================================

class LocationPoint(BaseModel):
    """Географическая точка"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteRequest(BaseModel):
    """Запрос на построение маршрута"""
    start_location: LocationPoint
    start_address: Optional[str] = None
    objects_count: int = Field(5, ge=2, le=20, description="Количество объектов в маршруте")
    
    @validator('start_location')
    def validate_moscow_coordinates(cls, v):
        # Проверяем, что координаты в пределах Москвы
        if not (37.0 <= v.longitude <= 38.0 and 55.0 <= v.latitude <= 56.0):
            raise ValueError('Координаты должны быть в пределах города Москвы')
        return v


class RouteObject(BaseModel):
    """Объект в маршруте"""
    sequence_number: int
    object: HeritageObject
    distance_from_previous: Optional[float] = None  # Расстояние от предыдущей точки (метры)


class RouteResponse(BaseModel):
    """Ответ с построенным маршрутом"""
    route_id: int
    start_location: LocationPoint
    start_address: Optional[str]
    total_distance: float  # Общее расстояние (метры)
    objects_count: int
    objects: List[RouteObject]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RouteHistory(BaseModel):
    """История маршрута (краткая информация)"""
    id: int
    start_address: Optional[str]
    total_distance: float
    objects_count: int
    is_favorite: bool = False
    created_at: datetime
    start_latitude: float
    start_longitude: float
    
    class Config:
        from_attributes = True


class RouteHistoryList(BaseModel):
    """Список истории маршрутов"""
    routes: List[RouteHistory]
    total: int


# ============================================
# Вспомогательные модели
# ============================================

class MessageResponse(BaseModel):
    """Общий ответ с сообщением"""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

