"""
Сервис построения маршрутов
"""
from typing import List, Dict, Optional, Tuple
from mysql.connector import Error
from database import get_db_cursor
from config import settings
import math


def find_nearest_objects(latitude: float, longitude: float, limit: int = 10, 
                         max_distance_km: float = 5.0) -> List[Dict]:
    """
    Найти N ближайших объектов культурного наследия от заданной точки
    
    Args:
        latitude: Широта точки старта
        longitude: Долгота точки старта
        limit: Количество объектов
        max_distance_km: Максимальное расстояние поиска (км)
        
    Returns:
        Список объектов с расстояниями
    """
    try:
        max_distance_meters = max_distance_km * 1000
        
        with get_db_cursor() as cursor:
            query = """
            SELECT 
                id,
                global_id,
                name,
                address,
                district,
                adm_area,
                object_type,
                category,
                security_status,
                description,
                build_year,
                ST_Y(location) as latitude,
                ST_X(location) as longitude,
                ST_Distance_Sphere(
                    location,
                    ST_GeomFromText(%s, 4326)
                ) as distance
            FROM heritage_objects
            WHERE ST_Distance_Sphere(
                location,
                ST_GeomFromText(%s, 4326)
            ) <= %s
            ORDER BY distance ASC
            LIMIT %s
            """
            
            point_wkt = f"POINT({longitude} {latitude})"
            cursor.execute(query, (point_wkt, point_wkt, max_distance_meters, limit))
            objects = cursor.fetchall()
            
            return objects
            
    except Error as e:
        print(f"Ошибка поиска ближайших объектов: {e}")
        return []


def calculate_distance_between_points(lat1: float, lon1: float, 
                                     lat2: float, lon2: float) -> float:
    """
    Вычислить расстояние между двумя точками (формула гаверсинуса)
    
    Args:
        lat1, lon1: Координаты первой точки
        lat2, lon2: Координаты второй точки
        
    Returns:
        Расстояние в метрах
    """
    R = 6371000  # Радиус Земли в метрах
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def build_greedy_route(start_lat: float, start_lon: float, 
                      objects: List[Dict]) -> List[Dict]:
    """
    Построить маршрут жадным алгоритмом (ближайший сосед)
    
    Args:
        start_lat: Широта точки старта
        start_lon: Долгота точки старта
        objects: Список объектов для посещения
        
    Returns:
        Упорядоченный список объектов с расстояниями
    """
    if not objects:
        return []
    
    route = []
    remaining = objects.copy()
    current_lat = start_lat
    current_lon = start_lon
    sequence = 1
    
    # Расстояние от старта до первого объекта
    first_distance = None
    
    while remaining:
        # Найти ближайший объект
        min_distance = float('inf')
        nearest_idx = 0
        
        for i, obj in enumerate(remaining):
            distance = calculate_distance_between_points(
                current_lat, current_lon,
                obj['latitude'], obj['longitude']
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        # Добавить ближайший объект в маршрут
        nearest_obj = remaining.pop(nearest_idx)
        
        # Сохранить расстояние от предыдущей точки
        if sequence == 1:
            first_distance = min_distance
        
        route_obj = {
            **nearest_obj,
            'sequence_number': sequence,
            'distance_from_previous': min_distance
        }
        
        route.append(route_obj)
        
        # Обновить текущую позицию
        current_lat = nearest_obj['latitude']
        current_lon = nearest_obj['longitude']
        sequence += 1
    
    return route


def calculate_total_distance(route: List[Dict]) -> float:
    """
    Вычислить общее расстояние маршрута
    
    Args:
        route: Список объектов маршрута
        
    Returns:
        Общее расстояние в метрах
    """
    total = 0.0
    for obj in route:
        if obj.get('distance_from_previous'):
            total += obj['distance_from_previous']
    return total


def save_route_to_db(user_id: int, start_lat: float, start_lon: float,
                    start_address: Optional[str], route: List[Dict]) -> Optional[int]:
    """
    Сохранить маршрут в базу данных
    
    Args:
        user_id: ID пользователя
        start_lat: Широта точки старта
        start_lon: Долгота точки старта
        start_address: Адрес точки старта
        route: Упорядоченный список объектов маршрута
        
    Returns:
        ID созданного маршрута или None
    """
    try:
        total_distance = calculate_total_distance(route)
        objects_count = len(route)
        
        with get_db_cursor(dictionary=False) as cursor:
            # Вставить маршрут
            point_wkt = f"POINT({start_lon} {start_lat})"
            
            cursor.execute(
                """
                INSERT INTO routes 
                (user_id, start_location, start_address, total_distance, objects_count)
                VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s, %s)
                """,
                (user_id, point_wkt, start_address, total_distance, objects_count)
            )
            
            route_id = cursor.lastrowid
            
            # Вставить объекты маршрута
            for obj in route:
                cursor.execute(
                    """
                    INSERT INTO route_objects
                    (route_id, object_id, sequence_number, distance_from_previous)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (route_id, obj['id'], obj['sequence_number'], obj['distance_from_previous'])
                )
            
            return route_id
            
    except Error as e:
        print(f"Ошибка сохранения маршрута: {e}")
        return None


def build_route(user_id: int, start_lat: float, start_lon: float,
               start_address: Optional[str], objects_count: int) -> Optional[Dict]:
    """
    Построить маршрут от точки старта
    
    Args:
        user_id: ID пользователя
        start_lat: Широта точки старта
        start_lon: Долгота точки старта
        start_address: Адрес точки старта
        objects_count: Количество объектов в маршруте
        
    Returns:
        Данные маршрута или None
    """
    # Ограничить количество объектов
    if objects_count > settings.MAX_ROUTE_OBJECTS:
        objects_count = settings.MAX_ROUTE_OBJECTS
    
    # Найти ближайшие объекты (берём с запасом)
    nearby_objects = find_nearest_objects(
        start_lat, start_lon,
        limit=objects_count * 2,  # Берём больше для лучшей оптимизации
        max_distance_km=settings.MAX_SEARCH_RADIUS_KM
    )
    
    if not nearby_objects:
        return None
    
    # Ограничить до нужного количества (берём только closest)
    nearby_objects = nearby_objects[:objects_count]
    
    # Построить маршрут жадным алгоритмом
    route = build_greedy_route(start_lat, start_lon, nearby_objects)
    
    if not route:
        return None
    
    # Сохранить маршрут в БД
    route_id = save_route_to_db(user_id, start_lat, start_lon, start_address, route)
    
    if not route_id:
        return None
    
    # Сформировать ответ
    total_distance = calculate_total_distance(route)
    
    return {
        'route_id': route_id,
        'start_lat': start_lat,
        'start_lon': start_lon,
        'start_address': start_address,
        'total_distance': total_distance,
        'objects_count': len(route),
        'objects': route
    }


def get_user_routes(user_id: int, limit: int = 50) -> List[Dict]:
    """
    Получить историю маршрутов пользователя
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество маршрутов
        
    Returns:
        Список маршрутов
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    id,
                    ST_Y(start_location) as start_latitude,
                    ST_X(start_location) as start_longitude,
                    start_address,
                    total_distance,
                    objects_count,
                    is_favorite,
                    created_at
                FROM routes
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            
            routes = cursor.fetchall()
            return routes
            
    except Error as e:
        print(f"Ошибка получения истории маршрутов: {e}")
        return []


def get_route_details(route_id: int, user_id: int) -> Optional[Dict]:
    """
    Получить детальную информацию о маршруте
    
    Args:
        route_id: ID маршрута
        user_id: ID пользователя (для проверки прав)
        
    Returns:
        Данные маршрута или None
    """
    try:
        with get_db_cursor() as cursor:
            # Получить маршрут
            cursor.execute(
                """
                SELECT 
                    id,
                    ST_Y(start_location) as start_latitude,
                    ST_X(start_location) as start_longitude,
                    start_address,
                    total_distance,
                    objects_count,
                    is_favorite,
                    created_at
                FROM routes
                WHERE id = %s AND user_id = %s
                """,
                (route_id, user_id)
            )
            
            route = cursor.fetchone()
            if not route:
                return None
            
            # Получить объекты маршрута
            cursor.execute(
                """
                SELECT 
                    ro.sequence_number,
                    ro.distance_from_previous,
                    h.id,
                    h.global_id,
                    h.name,
                    h.address,
                    h.district,
                    h.adm_area,
                    h.object_type,
                    h.category,
                    h.security_status,
                    h.description,
                    h.build_year,
                    ST_Y(h.location) as latitude,
                    ST_X(h.location) as longitude
                FROM route_objects ro
                JOIN heritage_objects h ON ro.object_id = h.id
                WHERE ro.route_id = %s
                ORDER BY ro.sequence_number ASC
                """,
                (route_id,)
            )
            
            objects = cursor.fetchall()
            
            return {
                **route,
                'objects': objects
            }
            
    except Error as e:
        print(f"Ошибка получения деталей маршрута: {e}")
        return None


def set_route_favorite(user_id: int, route_id: int, is_favorite: bool) -> bool:
    """
    Установить избранный статус маршрута
    """
    try:
        with get_db_cursor(dictionary=False) as cursor:
            cursor.execute(
                """
                UPDATE routes
                SET is_favorite = %s
                WHERE id = %s AND user_id = %s
                """,
                (is_favorite, route_id, user_id)
            )
            return cursor.rowcount > 0
    except Error as e:
        print(f"Ошибка обновления избранного маршрута: {e}")
        return False

