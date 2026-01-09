"""
Сервис аутентификации и авторизации
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from mysql.connector import Error
from config import settings
from database import get_db_cursor


# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хэширование пароля
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        Хэш пароля
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хэш пароля из БД
        
    Returns:
        True если пароль верный
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    
    Args:
        data: Данные для кодирования в токен
        expires_delta: Время жизни токена
        
    Returns:
        JWT токен
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Декодирование JWT токена
    
    Args:
        token: JWT токен
        
    Returns:
        Данные из токена или None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_username(username: str) -> Optional[dict]:
    """
    Получить пользователя по имени
    
    Args:
        username: Имя пользователя
        
    Returns:
        Данные пользователя или None
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, password_hash, full_name, 
                       created_at, last_login, is_active
                FROM users 
                WHERE username = %s
                """,
                (username,)
            )
            user = cursor.fetchone()
            return user
    except Error as e:
        print(f"Ошибка получения пользователя: {e}")
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """
    Получить пользователя по email
    
    Args:
        email: Email пользователя
        
    Returns:
        Данные пользователя или None
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, password_hash, full_name,
                       created_at, last_login, is_active
                FROM users 
                WHERE email = %s
                """,
                (email,)
            )
            user = cursor.fetchone()
            return user
    except Error as e:
        print(f"Ошибка получения пользователя: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    Получить пользователя по ID
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Данные пользователя или None
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, full_name, created_at, last_login, is_active
                FROM users 
                WHERE id = %s AND is_active = TRUE
                """,
                (user_id,)
            )
            user = cursor.fetchone()
            return user
    except Error as e:
        print(f"Ошибка получения пользователя: {e}")
        return None


def create_user(username: str, email: str, password: str, full_name: Optional[str] = None) -> Optional[int]:
    """
    Создание нового пользователя
    
    Args:
        username: Имя пользователя
        email: Email
        password: Пароль
        full_name: Полное имя
        
    Returns:
        ID созданного пользователя или None
    """
    try:
        password_hash = hash_password(password)
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name)
                VALUES (%s, %s, %s, %s)
                """,
                (username, email, password_hash, full_name)
            )
            user_id = cursor.lastrowid
            return user_id
    except Error as e:
        print(f"Ошибка создания пользователя: {e}")
        return None


def update_last_login(user_id: int):
    """
    Обновить время последнего входа
    
    Args:
        user_id: ID пользователя
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (user_id,)
            )
    except Error as e:
        print(f"Ошибка обновления last_login: {e}")


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Аутентификация пользователя
    
    Args:
        username: Имя пользователя
        password: Пароль
        
    Returns:
        Данные пользователя или None
    """
    user = get_user_by_username(username)
    
    if not user:
        return None
    
    if not user.get('is_active'):
        return None
    
    if not verify_password(password, user['password_hash']):
        return None
    
    # Обновляем время последнего входа
    update_last_login(user['id'])
    
    return user

