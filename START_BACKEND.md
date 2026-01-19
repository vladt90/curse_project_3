# Запуск Backend сервера

## Быстрый старт

### Шаг 1: Перейдите в папку backend

```powershell
cd ..
cd backend
```

### Шаг 2: Установите зависимости

```powershell
pip install -r requirements.txt
```

Должны установиться:
- fastapi
- uvicorn
- mysql-connector-python
- pydantic
- python-jose
- passlib
- и другие

### Шаг 3: Запустите сервер

```powershell
python main.py
```

**ИЛИ**

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Ожидаемый результат

```
============================================================
🚀 Запуск Heritage Routes System v1.0.0
============================================================
✓ Пул соединений с MySQL создан
✓ Подключение к базе данных успешно
✓ Сервер запущен на http://localhost:8000
✓ Документация API: http://localhost:8000/docs
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Проверка работы

Откройте в браузере:
- **Главная страница API:** http://localhost:8000
- **Swagger документация:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

## Возможные проблемы

### 1. uvicorn не найден

**Ошибка:**
```
uvicorn : Имя "uvicorn" не распознано...
```

**Решение:**
```powershell
pip install uvicorn
```

### 2. MySQL не подключается

**Ошибка:**
```
✗ Ошибка подключения к MySQL
```

**Решение:**
- Убедитесь что MySQL запущен в XAMPP
- Проверьте `backend/config.py` - параметры подключения

### 3. ModuleNotFoundError

**Ошибка:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Решение:**
```powershell
pip install -r requirements.txt
```

## Следующий шаг

После запуска backend откройте frontend:

1. Откройте новый терминал
2. Перейдите в папку frontend:
   ```powershell
   cd frontend
   python -m http.server 5500
   ```
3. Откройте браузер: http://localhost:5500/login.html
4. Войдите в созданный вами аккаунт (или зарегистрируйтесь через `/api/register`)

## Остановка сервера

Нажмите `Ctrl+C` в терминале где запущен uvicorn

