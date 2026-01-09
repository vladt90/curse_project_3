"""
Конфигурация подключения к базе данных
"""

# Параметры подключения к MySQL (XAMPP)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'heritage_routes',
    'port': 3306,
    'charset': 'utf8mb4'
}

# Настройки импорта данных
IMPORT_CONFIG = {
    'data_file': '../data.json',
    'batch_size': 500,  # Количество записей для вставки за раз
    'max_radius_km': 5,  # Максимальный радиус поиска объектов (км)
}

