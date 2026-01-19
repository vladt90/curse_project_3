"""
API эндпоинты для работы с объектами культурного наследия
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from models import HeritageObject, HeritageObjectList
from database import get_db_cursor
from mysql.connector import Error
from routes.auth import get_current_user
from services.story_service import get_story_for_object


router = APIRouter(prefix="/api", tags=["objects"])


@router.get("/objects", response_model=HeritageObjectList)
async def get_objects(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Количество объектов на странице"),
    district: Optional[str] = Query(None, description="Фильтр по району"),
    object_type: Optional[str] = Query(None, description="Фильтр по типу объекта"),
    search: Optional[str] = Query(None, description="Поиск по названию или адресу")
):
    """
    Получить список объектов культурного наследия с фильтрами и пагинацией
    
    Args:
        page: Номер страницы
        page_size: Размер страницы
        district: Фильтр по району
        object_type: Фильтр по типу
        search: Поиск по названию/адресу
        
    Returns:
        Список объектов с пагинацией
    """
    try:
        offset = (page - 1) * page_size
        
        # Строим запрос
        where_clauses = []
        params = []
        
        if district:
            where_clauses.append("district = %s")
            params.append(district)
        
        if object_type:
            where_clauses.append("object_type = %s")
            params.append(object_type)
        
        if search:
            where_clauses.append("(name LIKE %s OR address LIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        with get_db_cursor() as cursor:
            # Получить общее количество
            count_query = f"SELECT COUNT(*) as total FROM heritage_objects WHERE {where_sql}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Получить объекты
            query = f"""
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
                ST_X(location) as longitude
            FROM heritage_objects
            WHERE {where_sql}
            ORDER BY id ASC
            LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, params + [page_size, offset])
            objects = cursor.fetchall()
            
            total_pages = (total + page_size - 1) // page_size
            
            return HeritageObjectList(
                objects=[HeritageObject(**obj) for obj in objects],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
            
    except Error as e:
        print(f"Ошибка получения объектов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных из базы"
        )


@router.get("/objects/{object_id}", response_model=HeritageObject)
async def get_object_by_id(object_id: int):
    """
    Получить объект по ID
    
    Args:
        object_id: ID объекта
        
    Returns:
        Данные объекта
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
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
                    ST_X(location) as longitude
                FROM heritage_objects
                WHERE id = %s
                """,
                (object_id,)
            )
            
            obj = cursor.fetchone()
            
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Объект не найден"
                )
            
            return HeritageObject(**obj)
            
    except HTTPException:
        raise
    except Error as e:
        print(f"Ошибка получения объекта: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных"
        )


@router.get("/objects/{object_id}/story")
async def get_object_story(
    object_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Получить рассказ (ИИ-экскурсовод) об объекте. Результат кэшируется в БД.
    """
    story = get_story_for_object(object_id)
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Объект не найден"
        )
    return {"story": story}


@router.get("/districts")
async def get_districts():
    """
    Получить список районов
    
    Returns:
        Список уникальных районов
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT district
                FROM heritage_objects
                WHERE district IS NOT NULL AND district != ''
                ORDER BY district ASC
                """
            )
            
            districts = [row['district'] for row in cursor.fetchall()]
            return {"districts": districts}
            
    except Error as e:
        print(f"Ошибка получения районов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных"
        )


@router.get("/object-types")
async def get_object_types():
    """
    Получить список типов объектов
    
    Returns:
        Список уникальных типов
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT object_type, COUNT(*) as count
                FROM heritage_objects
                WHERE object_type IS NOT NULL AND object_type != ''
                GROUP BY object_type
                ORDER BY count DESC
                """
            )
            
            types = cursor.fetchall()
            return {"object_types": types}
            
    except Error as e:
        print(f"Ошибка получения типов объектов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных"
        )

