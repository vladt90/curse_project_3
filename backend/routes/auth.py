"""
API эндпоинты для аутентификации
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from models import UserCreate, UserLogin, Token, UserResponse, MessageResponse
from services.auth_service import (
    create_user, authenticate_user, get_user_by_username,
    get_user_by_email, get_user_by_id, create_access_token, decode_token
)


router = APIRouter(prefix="/api", tags=["auth"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Получить текущего пользователя из токена
    
    Args:
        credentials: HTTP Bearer токен
        
    Returns:
        Данные пользователя
        
    Raises:
        HTTPException: Если токен невалидный
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен аутентификации"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен аутентификации"
        )
    
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Регистрация нового пользователя
    
    Args:
        user_data: Данные для регистрации
        
    Returns:
        Токен авторизации и данные пользователя
    """
    # Проверить существование пользователя
    existing_user = get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    existing_email = get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Создать пользователя
    user_id = create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания пользователя"
        )
    
    # Получить созданного пользователя
    user = get_user_by_id(user_id)
    
    # Создать токен
    access_token = create_access_token(data={"user_id": user_id})
    
    return Token(
        access_token=access_token,
        user=UserResponse(**user)
    )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """
    Вход пользователя
    
    Args:
        user_data: Логин и пароль
        
    Returns:
        Токен авторизации и данные пользователя
    """
    # Аутентификация
    user = authenticate_user(user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    # Создать токен
    access_token = create_access_token(data={"user_id": user['id']})
    
    return Token(
        access_token=access_token,
        user=UserResponse(**user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Получить информацию о текущем пользователе
    
    Args:
        current_user: Текущий пользователь из токена
        
    Returns:
        Данные пользователя
    """
    return UserResponse(**current_user)

