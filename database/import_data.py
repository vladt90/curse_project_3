"""
Скрипт импорта данных об объектах культурного наследия
из JSON файла в базу данных MySQL
"""

import json
import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Tuple, Optional
import sys
import os
from config import DB_CONFIG, IMPORT_CONFIG


def calculate_centroid(coordinates: List) -> Optional[Tuple[float, float]]:
    """
    Вычисляет центроид (центр масс) полигона
    
    Args:
        coordinates: Список координат полигона [[lon, lat], ...]
        
    Returns:
        Tuple (longitude, latitude) или None если данные некорректны
    """
    try:
        if not coordinates or len(coordinates) == 0:
            return None
            
        # Если это вложенный список (полигон с дырками)
        if isinstance(coordinates[0][0], list):
            coordinates = coordinates[0]
        
        # Вычисляем среднее значение координат
        total_lon = 0
        total_lat = 0
        count = 0
        
        for coord in coordinates:
            if len(coord) >= 2:
                total_lon += coord[0]
                total_lat += coord[1]
                count += 1
        
        if count == 0:
            return None
            
        centroid_lon = total_lon / count
        centroid_lat = total_lat / count
        
        return (centroid_lon, centroid_lat)
        
    except Exception as e:
        print(f"Ошибка вычисления центроида: {e}")
        return None


def clean_text(text: str) -> str:
    """
    Очищает текст от лишних символов и пробелов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    return text.strip().replace('\x00', '')


def parse_json_data(file_path: str) -> List[Dict]:
    """
    Парсит JSON файл с данными
    
    Args:
        file_path: Путь к JSON файлу
        
    Returns:
        Список словарей с данными объектов
    """
    print(f"Загрузка данных из {file_path}...")
    
    # Пробуем разные кодировки
    encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'windows-1251', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            
            print(f"✓ Файл успешно прочитан (кодировка: {encoding})")
            
            if isinstance(data, list):
                print(f"✓ Загружено {len(data)} объектов")
                return data
            else:
                print("Ошибка: JSON файл не содержит массив объектов")
                return []
                
        except (UnicodeDecodeError, UnicodeError):
            # Пробуем следующую кодировку
            continue
        except FileNotFoundError:
            print(f"✗ Ошибка: Файл {file_path} не найден")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ Ошибка парсинга JSON: {e}")
            return []
        except Exception as e:
            print(f"✗ Ошибка при чтении с кодировкой {encoding}: {e}")
            continue
    
    print(f"✗ Не удалось прочитать файл ни с одной из кодировок: {encodings}")
    return []


def process_object(obj: Dict) -> Optional[Dict]:
    """
    Обрабатывает один объект из JSON
    
    Args:
        obj: Словарь с данными объекта
        
    Returns:
        Обработанный словарь или None если объект некорректен
    """
    try:
        # Получаем координаты
        geo_data = obj.get('geoData', {})
        coordinates = geo_data.get('coordinates', [])
        
        if not coordinates:
            return None
        
        # Вычисляем центроид
        centroid = calculate_centroid(coordinates)
        if not centroid:
            return None
        
        lon, lat = centroid
        
        # Проверяем корректность координат (Москва)
        if not (37.0 <= lon <= 38.0 and 55.0 <= lat <= 56.0):
            return None
        
        # Получаем название
        name = clean_text(obj.get('ObjectNameOnDoc', '') or obj.get('ObjectName', ''))
        if not name:
            return None
        
        # Формируем обработанный объект
        processed = {
            'global_id': obj.get('global_id'),
            'name': name[:500],  # Ограничиваем длину
            'address': clean_text(obj.get('Addresses', ''))[:500],
            'district': clean_text(obj.get('District', ''))[:200],
            'adm_area': clean_text(obj.get('AdmArea', ''))[:200],
            'object_type': clean_text(obj.get('ObjectType', ''))[:200],
            'category': clean_text(obj.get('Category', ''))[:200],
            'security_status': clean_text(obj.get('SecurityStatus', ''))[:200],
            'description': clean_text(obj.get('EnsembleNameOnDoc', '') or obj.get('EnsembleName', '')),
            'build_year': '',  # В данных нет года постройки
            'longitude': lon,
            'latitude': lat
        }
        
        return processed
        
    except Exception as e:
        print(f"Ошибка обработки объекта: {e}")
        return None


def connect_to_database() -> Optional[mysql.connector.MySQLConnection]:
    """
    Создает подключение к базе данных
    
    Returns:
        Объект подключения или None в случае ошибки
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print(f"✓ Подключение к MySQL установлено")
            return connection
    except Error as e:
        print(f"✗ Ошибка подключения к MySQL: {e}")
        return None


def import_objects(connection: mysql.connector.MySQLConnection, objects: List[Dict]) -> int:
    """
    Импортирует объекты в базу данных
    
    Args:
        connection: Подключение к БД
        objects: Список обработанных объектов
        
    Returns:
        Количество импортированных объектов
    """
    cursor = connection.cursor()
    imported_count = 0
    skipped_count = 0
    batch_size = IMPORT_CONFIG['batch_size']
    
    # SQL запрос для вставки
    insert_query = """
    INSERT INTO heritage_objects 
    (global_id, name, address, district, adm_area, object_type, category, 
     security_status, description, build_year, location)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        address = VALUES(address),
        district = VALUES(district),
        adm_area = VALUES(adm_area),
        object_type = VALUES(object_type),
        category = VALUES(category),
        security_status = VALUES(security_status),
        description = VALUES(description)
    """
    
    print(f"\nНачало импорта {len(objects)} объектов...")
    
    batch = []
    for i, obj in enumerate(objects, 1):
        try:
            # Формируем WKT строку для POINT
            point_wkt = f"POINT({obj['longitude']} {obj['latitude']})"
            
            values = (
                obj['global_id'],
                obj['name'],
                obj['address'],
                obj['district'],
                obj['adm_area'],
                obj['object_type'],
                obj['category'],
                obj['security_status'],
                obj['description'],
                obj['build_year'],
                point_wkt
            )
            
            batch.append(values)
            
            # Вставляем батчами
            if len(batch) >= batch_size or i == len(objects):
                cursor.executemany(insert_query, batch)
                connection.commit()
                imported_count += len(batch)
                print(f"  Импортировано {imported_count}/{len(objects)} объектов...", end='\r')
                batch = []
                
        except Error as e:
            skipped_count += 1
            if skipped_count <= 5:  # Показываем первые 5 ошибок
                print(f"\n  Ошибка вставки объекта {obj.get('name', 'Неизвестно')}: {e}")
    
    cursor.close()
    print(f"\n✓ Импорт завершен: {imported_count} объектов импортировано, {skipped_count} пропущено")
    return imported_count


def get_statistics(connection: mysql.connector.MySQLConnection):
    """
    Выводит статистику по импортированным данным
    
    Args:
        connection: Подключение к БД
    """
    cursor = connection.cursor()
    
    print("\n" + "="*60)
    print("СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("="*60)
    
    # Общее количество объектов
    cursor.execute("SELECT COUNT(*) FROM heritage_objects")
    total = cursor.fetchone()[0]
    print(f"Всего объектов в базе: {total}")
    
    # По районам
    cursor.execute("""
        SELECT district, COUNT(*) as count 
        FROM heritage_objects 
        WHERE district IS NOT NULL AND district != ''
        GROUP BY district 
        ORDER BY count DESC 
        LIMIT 10
    """)
    print("\nТоп-10 районов по количеству объектов:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # По типам
    cursor.execute("""
        SELECT object_type, COUNT(*) as count 
        FROM heritage_objects 
        WHERE object_type IS NOT NULL AND object_type != ''
        GROUP BY object_type 
        ORDER BY count DESC 
        LIMIT 5
    """)
    print("\nТоп-5 типов объектов:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.close()
    print("="*60)


def main():
    """
    Главная функция импорта
    """
    print("="*60)
    print("ИМПОРТ ДАННЫХ О КУЛЬТУРНОМ НАСЛЕДИИ МОСКВЫ")
    print("="*60)
    
    # Определяем путь к файлу данных
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, IMPORT_CONFIG['data_file'])
    
    # Проверяем существование файла
    if not os.path.exists(data_file):
        print(f"✗ Ошибка: Файл {data_file} не найден")
        sys.exit(1)
    
    # Загружаем данные
    raw_data = parse_json_data(data_file)
    if not raw_data:
        print("✗ Нет данных для импорта")
        sys.exit(1)
    
    # Обрабатываем объекты
    print("\nОбработка объектов...")
    processed_objects = []
    for obj in raw_data:
        processed = process_object(obj)
        if processed:
            processed_objects.append(processed)
    
    print(f"✓ Обработано {len(processed_objects)} из {len(raw_data)} объектов")
    
    if not processed_objects:
        print("✗ Нет корректных объектов для импорта")
        sys.exit(1)
    
    # Подключаемся к БД
    connection = connect_to_database()
    if not connection:
        sys.exit(1)
    
    try:
        # Импортируем данные
        imported_count = import_objects(connection, processed_objects)
        
        # Выводим статистику
        if imported_count > 0:
            get_statistics(connection)
        
        print("\n✓ Импорт успешно завершен!")
        
    except Exception as e:
        print(f"\n✗ Ошибка во время импорта: {e}")
        sys.exit(1)
    finally:
        if connection.is_connected():
            connection.close()
            print("\nПодключение к БД закрыто")


if __name__ == "__main__":
    main()

