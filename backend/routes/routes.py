"""
API эндпоинты для работы с маршрутами
"""
from fastapi import APIRouter, HTTPException, status, Depends
from mysql.connector import Error
from typing import List
from datetime import datetime
from models import (
    RouteRequest, RouteResponse, RouteObject, RouteHistory,
    RouteHistoryList, LocationPoint, HeritageObject, MessageResponse
)
from services.route_service import (
    build_route, get_user_routes, get_route_details, set_route_favorite
)
from routes.auth import get_current_user


router = APIRouter(prefix="/api", tags=["routes"])


@router.post("/route", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    route_request: RouteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Построить новый маршрут от заданной точки старта
    
    Args:
        route_request: Параметры маршрута (точка старта, количество объектов)
        current_user: Текущий пользователь
        
    Returns:
        Построенный маршрут с объектами
    """
    user_id = current_user['id']
    
    # Построить маршрут
    route_data = build_route(
        user_id=user_id,
        start_lat=route_request.start_location.latitude,
        start_lon=route_request.start_location.longitude,
        start_address=route_request.start_address,
        objects_count=route_request.objects_count
    )
    
    if not route_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не найдено объектов культурного наследия в указанном радиусе"
        )
    
    # Форматировать ответ
    route_objects = []
    for obj in route_data['objects']:
        heritage_obj = HeritageObject(
            id=obj['id'],
            global_id=obj['global_id'],
            name=obj['name'],
            address=obj['address'],
            district=obj.get('district'),
            adm_area=obj.get('adm_area'),
            object_type=obj.get('object_type'),
            category=obj.get('category'),
            security_status=obj.get('security_status'),
            description=obj.get('description'),
            build_year=obj.get('build_year'),
            latitude=obj['latitude'],
            longitude=obj['longitude'],
            distance=obj.get('distance')
        )
        
        route_objects.append(RouteObject(
            sequence_number=obj['sequence_number'],
            object=heritage_obj,
            distance_from_previous=obj.get('distance_from_previous')
        ))
    
    return RouteResponse(
        route_id=route_data['route_id'],
        start_location=LocationPoint(
            latitude=route_data['start_lat'],
            longitude=route_data['start_lon']
        ),
        start_address=route_data['start_address'],
        total_distance=route_data['total_distance'],
        objects_count=route_data['objects_count'],
        objects=route_objects,
        created_at=datetime.now()
    )


@router.get("/routes", response_model=RouteHistoryList)
async def get_routes(current_user: dict = Depends(get_current_user)):
    """
    Получить историю маршрутов текущего пользователя
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        Список маршрутов пользователя
    """
    user_id = current_user['id']
    
    routes = get_user_routes(user_id, limit=50)
    
    route_list = []
    for route in routes:
        route_list.append(RouteHistory(
            id=route['id'],
            start_address=route.get('start_address'),
            total_distance=route['total_distance'],
            objects_count=route['objects_count'],
            is_favorite=bool(route.get('is_favorite', False)),
            created_at=route['created_at'],
            start_latitude=route['start_latitude'],
            start_longitude=route['start_longitude']
        ))
    
    return RouteHistoryList(
        routes=route_list,
        total=len(route_list)
    )


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Получить детальную информацию о маршруте
    
    Args:
        route_id: ID маршрута
        current_user: Текущий пользователь
        
    Returns:
        Полные данные маршрута с объектами
    """
    user_id = current_user['id']
    
    route_data = get_route_details(route_id, user_id)
    
    if not route_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Маршрут не найден или у вас нет прав доступа"
        )
    
    # Форматировать ответ
    route_objects = []
    for obj in route_data['objects']:
        heritage_obj = HeritageObject(
            id=obj['id'],
            global_id=obj['global_id'],
            name=obj['name'],
            address=obj['address'],
            district=obj.get('district'),
            adm_area=obj.get('adm_area'),
            object_type=obj.get('object_type'),
            category=obj.get('category'),
            security_status=obj.get('security_status'),
            description=obj.get('description'),
            build_year=obj.get('build_year'),
            latitude=obj['latitude'],
            longitude=obj['longitude']
        )
        
        route_objects.append(RouteObject(
            sequence_number=obj['sequence_number'],
            object=heritage_obj,
            distance_from_previous=obj.get('distance_from_previous')
        ))
    
    return RouteResponse(
        route_id=route_data['id'],
        start_location=LocationPoint(
            latitude=route_data['start_latitude'],
            longitude=route_data['start_longitude']
        ),
        start_address=route_data.get('start_address'),
        total_distance=route_data['total_distance'],
        objects_count=route_data['objects_count'],
        objects=route_objects,
        created_at=route_data['created_at']
    )


@router.patch("/routes/{route_id}/favorite", response_model=MessageResponse)
async def update_route_favorite(
    route_id: int,
    is_favorite: bool,
    current_user: dict = Depends(get_current_user)
):
    """
    Установить/снять избранный статус маршрута
    """
    user_id = current_user['id']
    try:
        updated = set_route_favorite(user_id, route_id, is_favorite)
    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления избранного: {e}"
        ) from e
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Маршрут не найден или у вас нет прав доступа"
        )
    return MessageResponse(message="Статус маршрута обновлен")

