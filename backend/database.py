"""
Подключение к базе данных MySQL
"""
import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional
from contextlib import contextmanager
from config import settings


# Пул соединений с БД
connection_pool = None


def init_connection_pool():
    """Инициализация пула соединений"""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="heritage_pool",
            pool_size=10,
            pool_reset_session=True,
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            port=settings.DB_PORT,
            charset='utf8mb4',
            autocommit=False
        )
        print("✓ Пул соединений с MySQL создан")
    except Error as e:
        print(f"✗ Ошибка создания пула соединений: {e}")
        raise


def get_connection():
    """
    Получить соединение из пула
    
    Returns:
        Соединение с БД
    """
    global connection_pool
    if connection_pool is None:
        init_connection_pool()
    
    try:
        return connection_pool.get_connection()
    except Error as e:
        print(f"Ошибка получения соединения: {e}")
        raise


@contextmanager
def get_db_connection():
    """
    Контекстный менеджер для работы с БД
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    conn = None
    try:
        conn = get_connection()
        yield conn
        conn.commit()
    except Error as e:
        if conn:
            conn.rollback()
        print(f"Ошибка БД: {e}")
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()


@contextmanager
def get_db_cursor(dictionary=True):
    """
    Контекстный менеджер для курсора БД
    
    Args:
        dictionary: Если True, возвращает результаты как словари
        
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT ...")
            results = cursor.fetchall()
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        conn.commit()
    except Error as e:
        if conn:
            conn.rollback()
        print(f"Ошибка БД: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def test_connection() -> bool:
    """
    Проверка подключения к БД
    
    Returns:
        True если подключение успешно
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"Ошибка проверки соединения: {e}")
        return False

