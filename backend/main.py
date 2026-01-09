"""
Главное приложение FastAPI
"""
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from config import settings
from database import init_connection_pool, test_connection
from routes import auth, objects, routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для приложения
    """
    # Startup
    print("="*60)
    print(f"🚀 Запуск {settings.APP_NAME} v{settings.APP_VERSION}")
    print("="*60)
    
    try:
        # Инициализация пула соединений
        init_connection_pool()
        
        # Проверка подключения к БД
        if test_connection():
            print("✓ Подключение к базе данных успешно")
        else:
            print("✗ Ошибка подключения к базе данных")
            raise Exception("Не удалось подключиться к БД")
        
        print(f"✓ Сервер запущен на http://localhost:8000")
        print(f"✓ Документация API: http://localhost:8000/docs")
        print("="*60)
        
    except Exception as e:
        print(f"✗ Ошибка запуска приложения: {e}")
        raise
    
    yield
    
    # Shutdown
    print("\n" + "="*60)
    print("🛑 Остановка сервера...")
    print("="*60)


# Создание приложения FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="REST API для построения туристических маршрутов по объектам культурного наследия Москвы",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключение роутеров
app.include_router(auth.router)
app.include_router(objects.router)
app.include_router(routes.router)


@app.get("/", tags=["root"])
async def root():
    """
    Корневой эндпоинт
    """
    return {
        "message": f"Добро пожаловать в {settings.APP_NAME}!",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["root"])
async def health_check():
    """
    Проверка работоспособности сервера
    """
    db_status = test_connection()
    
    if db_status:
        return {
            "status": "healthy",
            "database": "connected",
            "version": settings.APP_VERSION
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "version": settings.APP_VERSION
            }
        )


# Обработка ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Глобальный обработчик ошибок
    """
    print(f"Необработанная ошибка: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Внутренняя ошибка сервера",
            "detail": str(exc) if settings.DEBUG else "Обратитесь к администратору"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

