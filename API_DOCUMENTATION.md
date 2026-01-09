# API Документация

## 📖 Обзор

REST API для системы планирования культурных маршрутов по объектам культурного наследия города Москвы.

**Base URL:** `http://localhost:8000/api`

**Документация:** 
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🔐 Аутентификация

API использует **JWT Bearer Token** аутентификацию.

### Получение токена

После регистрации или входа вы получаете токен доступа:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@heritage.ru"
  }
}
```

### Использование токена

Добавьте заголовок к запросам:

```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 📝 Эндпоинты

### 1. Аутентификация

#### POST /api/register
Регистрация нового пользователя

**Body:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "full_name": "Иван Иванов"  // необязательно
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "Иван Иванов",
    "created_at": "2025-01-09T00:00:00"
  }
}
```

**Errors:**
- `400` - Пользователь уже существует
- `500` - Ошибка сервера

---

#### POST /api/login
Вход пользователя

**Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@heritage.ru",
    "full_name": "Администратор системы",
    "created_at": "2025-01-09T00:00:00",
    "last_login": "2025-01-09T10:30:00"
  }
}
```

**Errors:**
- `401` - Неверные учетные данные

---

#### GET /api/me
Получить информацию о текущем пользователе

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response (200):**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@heritage.ru",
  "full_name": "Администратор системы",
  "created_at": "2025-01-09T00:00:00",
  "last_login": "2025-01-09T10:30:00"
}
```

---

### 2. Объекты культурного наследия

#### GET /api/objects
Получить список объектов с фильтрами и пагинацией

**Query параметры:**
- `page` (int) - Номер страницы (default: 1)
- `page_size` (int) - Размер страницы (default: 20, max: 100)
- `district` (string) - Фильтр по району
- `object_type` (string) - Фильтр по типу объекта
- `search` (string) - Поиск по названию или адресу

**Пример:**
```
GET /api/objects?page=1&page_size=10&district=Центральный район
```

**Response (200):**
```json
{
  "objects": [
    {
      "id": 1,
      "global_id": 2949468,
      "name": "Усадебный дом, 1895 г., арх. А.К.Буров",
      "address": "Кисловодская улица, дом 5, строение 7",
      "district": "Ломоносовский район",
      "adm_area": "Юго-Западный административный округ",
      "object_type": "Сооружение",
      "category": "Региональная значимость",
      "security_status": "Объект культурного наследия",
      "description": "",
      "build_year": "",
      "latitude": 55.758190957,
      "longitude": 37.568926108,
      "distance": null
    }
  ],
  "total": 5832,
  "page": 1,
  "page_size": 10,
  "total_pages": 584
}
```

---

#### GET /api/objects/{object_id}
Получить объект по ID

**Response (200):**
```json
{
  "id": 1,
  "global_id": 2949468,
  "name": "Усадебный дом, 1895 г.",
  "address": "Кисловодская улица, дом 5",
  "district": "Ломоносовский район",
  "object_type": "Сооружение",
  "latitude": 55.758190957,
  "longitude": 37.568926108
}
```

**Errors:**
- `404` - Объект не найден

---

#### GET /api/districts
Получить список районов

**Response (200):**
```json
{
  "districts": [
    "Центральный район",
    "Тверской район",
    "Арбат",
    "..."
  ]
}
```

---

#### GET /api/object-types
Получить типы объектов

**Response (200):**
```json
{
  "object_types": [
    {
      "object_type": "Сооружение",
      "count": 3245
    },
    {
      "object_type": "Ансамбль",
      "count": 1532
    }
  ]
}
```

---

### 3. Маршруты

#### POST /api/route
Построить новый маршрут 🔒

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Body:**
```json
{
  "start_location": {
    "latitude": 55.7539,
    "longitude": 37.6208
  },
  "objects_count": 5,
  "start_address": "Красная площадь"  // необязательно
}
```

**Validation:**
- `latitude`: от -90 до 90
- `longitude`: от -180 до 180
- `objects_count`: от 2 до 20
- Координаты должны быть в пределах Москвы (37-38°E, 55-56°N)

**Response (201):**
```json
{
  "route_id": 123,
  "start_location": {
    "latitude": 55.7539,
    "longitude": 37.6208
  },
  "start_address": "Красная площадь",
  "total_distance": 3542.75,
  "objects_count": 5,
  "objects": [
    {
      "sequence_number": 1,
      "object": {
        "id": 245,
        "name": "Исторический музей",
        "address": "Красная площадь, 1",
        "latitude": 55.7556,
        "longitude": 37.6173,
        "object_type": "Музей"
      },
      "distance_from_previous": 235.5
    },
    {
      "sequence_number": 2,
      "object": { "..." },
      "distance_from_previous": 428.3
    }
  ],
  "created_at": "2025-01-09T10:30:00"
}
```

**Errors:**
- `401` - Требуется авторизация
- `404` - Не найдено объектов в указанном радиусе
- `422` - Ошибка валидации данных

---

#### GET /api/routes
Получить историю маршрутов пользователя 🔒

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response (200):**
```json
{
  "routes": [
    {
      "id": 123,
      "start_address": "Красная площадь",
      "total_distance": 3542.75,
      "objects_count": 5,
      "created_at": "2025-01-09T10:30:00",
      "start_latitude": 55.7539,
      "start_longitude": 37.6208
    },
    {
      "id": 122,
      "start_address": "Парк Горького",
      "total_distance": 4127.25,
      "objects_count": 7,
      "created_at": "2025-01-08T15:20:00",
      "start_latitude": 55.7304,
      "start_longitude": 37.6019
    }
  ],
  "total": 2
}
```

---

#### GET /api/routes/{route_id}
Получить детали маршрута 🔒

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response (200):**
```json
{
  "route_id": 123,
  "start_location": {
    "latitude": 55.7539,
    "longitude": 37.6208
  },
  "start_address": "Красная площадь",
  "total_distance": 3542.75,
  "objects_count": 5,
  "objects": [
    {
      "sequence_number": 1,
      "object": {
        "id": 245,
        "name": "Исторический музей",
        "address": "Красная площадь, 1",
        "district": "Тверской район",
        "object_type": "Музей",
        "latitude": 55.7556,
        "longitude": 37.6173
      },
      "distance_from_previous": 235.5
    }
  ],
  "created_at": "2025-01-09T10:30:00"
}
```

**Errors:**
- `401` - Требуется авторизация
- `404` - Маршрут не найден или нет доступа

---

## 🔄 Коды ответов

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 201 | Ресурс создан |
| 400 | Ошибка в запросе |
| 401 | Требуется авторизация |
| 404 | Ресурс не найден |
| 422 | Ошибка валидации |
| 500 | Ошибка сервера |

---

## 📊 Примеры использования

### Python

```python
import requests

# Вход
response = requests.post('http://localhost:8000/api/login', json={
    'username': 'admin',
    'password': 'admin123'
})
token = response.json()['access_token']

# Построение маршрута
headers = {'Authorization': f'Bearer {token}'}
route_data = {
    'start_location': {
        'latitude': 55.7539,
        'longitude': 37.6208
    },
    'objects_count': 5
}
response = requests.post(
    'http://localhost:8000/api/route',
    headers=headers,
    json=route_data
)
route = response.json()
print(f"Маршрут построен! ID: {route['route_id']}")
```

### JavaScript (Fetch)

```javascript
// Вход
const loginResponse = await fetch('http://localhost:8000/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'admin',
        password: 'admin123'
    })
});
const { access_token } = await loginResponse.json();

// Построение маршрута
const routeResponse = await fetch('http://localhost:8000/api/route', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${access_token}`
    },
    body: JSON.stringify({
        start_location: { latitude: 55.7539, longitude: 37.6208 },
        objects_count: 5
    })
});
const route = await routeResponse.json();
console.log('Маршрут построен!', route);
```

---

## ⚙️ Лимиты и ограничения

- **Максимальное количество объектов в маршруте:** 20
- **Максимальный радиус поиска:** 5 км
- **Время жизни токена:** 24 часа
- **Размер страницы (objects):** максимум 100

---

## 🛡️ Безопасность

- Пароли хэшируются с использованием **bcrypt**
- JWT токены подписаны секретным ключом
- SQL инъекции предотвращены использованием **prepared statements**
- CORS настроен для cross-origin запросов

