-- ======================================================
-- Схема базы данных для системы планирования
-- культурных маршрутов города Москвы
-- ======================================================

-- Использование базы данных
USE heritage_routes;

-- ======================================================
-- Таблица объектов культурного наследия
-- ======================================================
DROP TABLE IF EXISTS object_stories;
DROP TABLE IF EXISTS route_objects;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS heritage_objects;

CREATE TABLE heritage_objects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    global_id BIGINT UNIQUE NOT NULL COMMENT 'Уникальный ID из открытых данных',
    name VARCHAR(500) NOT NULL COMMENT 'Название объекта',
    address VARCHAR(500) NOT NULL COMMENT 'Адрес объекта',
    district VARCHAR(200) COMMENT 'Район',
    adm_area VARCHAR(200) COMMENT 'Административный округ',
    object_type VARCHAR(200) COMMENT 'Тип объекта (здание, памятник и т.д.)',
    category VARCHAR(200) COMMENT 'Категория объекта',
    security_status VARCHAR(200) COMMENT 'Статус охраны',
    description TEXT COMMENT 'Описание объекта',
    build_year VARCHAR(100) COMMENT 'Год постройки',
    location POINT NOT NULL COMMENT 'Координаты объекта (широта, долгота)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    KEY idx_district (district),
    KEY idx_object_type (object_type),
    KEY idx_category (category),
    SPATIAL KEY idx_location (location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Объекты культурного наследия города Москвы';

-- ======================================================
-- Таблица пользователей
-- ======================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL COMMENT 'Имя пользователя',
    email VARCHAR(255) UNIQUE NOT NULL COMMENT 'Email',
    password_hash VARCHAR(255) NOT NULL COMMENT 'Хэш пароля (bcrypt)',
    full_name VARCHAR(255) COMMENT 'Полное имя',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активен ли пользователь',
    
    KEY idx_email (email),
    KEY idx_username (username),
    KEY idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Зарегистрированные пользователи системы';

-- ======================================================
-- Таблица маршрутов
-- ======================================================
CREATE TABLE routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT 'ID пользователя',
    start_location POINT NOT NULL COMMENT 'Точка старта маршрута',
    start_address VARCHAR(500) COMMENT 'Адрес точки старта',
    total_distance DECIMAL(10, 2) COMMENT 'Общая длина маршрута в метрах',
    objects_count INT NOT NULL COMMENT 'Количество объектов в маршруте',
    is_favorite BOOLEAN DEFAULT FALSE COMMENT 'Избранный маршрут',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата и время построения маршрута',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    KEY idx_user_id (user_id),
    KEY idx_created_at (created_at),
    SPATIAL KEY idx_start_location (start_location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Построенные маршруты пользователей';

-- ======================================================
-- Таблица связей маршрутов и объектов
-- ======================================================
CREATE TABLE route_objects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT NOT NULL COMMENT 'ID маршрута',
    object_id INT NOT NULL COMMENT 'ID объекта культурного наследия',
    sequence_number INT NOT NULL COMMENT 'Порядковый номер объекта в маршруте (1, 2, 3...)',
    distance_from_previous DECIMAL(10, 2) COMMENT 'Расстояние от предыдущей точки в метрах',
    
    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE,
    FOREIGN KEY (object_id) REFERENCES heritage_objects(id) ON DELETE CASCADE,
    
    KEY idx_route_id (route_id),
    KEY idx_object_id (object_id),
    KEY idx_sequence (route_id, sequence_number),
    
    UNIQUE KEY unique_route_object (route_id, object_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Связь маршрутов и объектов наследия';

-- ======================================================
-- Таблица рассказов (ИИ-экскурсовод) - кэш
-- ======================================================
CREATE TABLE IF NOT EXISTS object_stories (
    object_id INT PRIMARY KEY,
    model VARCHAR(200) NOT NULL,
    story TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES heritage_objects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Кэш рассказов об объектах (генерация через LLM)';

-- ======================================================
-- Вспомогательные функции и процедуры
-- ======================================================

-- Функция для вычисления расстояния между двумя точками в метрах
DELIMITER //
CREATE FUNCTION calculate_distance(point1 POINT, point2 POINT)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
BEGIN
    RETURN ST_Distance_Sphere(point1, point2);
END //
DELIMITER ;

-- ======================================================
-- Примечание
-- ======================================================
-- Тестовые учётные данные не добавляются в схему намеренно.
-- Создайте пользователя через регистрацию (/api/register) или добавьте сид-скрипт локально для dev.

-- ======================================================
-- Примеры запросов для работы с пространственными данными
-- ======================================================

-- Найти N ближайших объектов от заданной точки (например, 10 объектов в радиусе 5 км)
-- Пример: точка старта - Красная площадь (55.7539, 37.6208)
/*
SELECT 
    id,
    name,
    address,
    object_type,
    ST_Distance_Sphere(location, ST_GeomFromText('POINT(37.6208 55.7539)', 4326)) AS distance_meters,
    ST_X(location) AS longitude,
    ST_Y(location) AS latitude
FROM heritage_objects
WHERE ST_Distance_Sphere(location, ST_GeomFromText('POINT(37.6208 55.7539)', 4326)) <= 5000
ORDER BY distance_meters ASC
LIMIT 10;
*/

-- Найти объекты в определенном радиусе (буфер)
/*
SELECT 
    id,
    name,
    address,
    ST_Distance_Sphere(location, ST_GeomFromText('POINT(37.6208 55.7539)', 4326)) AS distance_meters
FROM heritage_objects
WHERE ST_Contains(
    ST_Buffer(ST_GeomFromText('POINT(37.6208 55.7539)', 4326), 0.05),
    location
);
*/

-- Получить информацию о маршруте с объектами
/*
SELECT 
    r.id as route_id,
    r.created_at,
    r.total_distance,
    ro.sequence_number,
    h.name,
    h.address,
    ro.distance_from_previous
FROM routes r
JOIN route_objects ro ON r.id = ro.route_id
JOIN heritage_objects h ON ro.object_id = h.id
WHERE r.user_id = 1
ORDER BY r.created_at DESC, ro.sequence_number ASC;
*/

-- ======================================================
-- Конец схемы
-- ======================================================

