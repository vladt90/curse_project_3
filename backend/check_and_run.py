"""
Проверка зависимостей и запуск сервера
"""
import sys
import subprocess

print("="*60)
print("Проверка установленных пакетов")
print("="*60)

required_packages = [
    'fastapi',
    'uvicorn',
    'mysql.connector',
    'pydantic',
    'pydantic_settings',
    'jose',
    'passlib',
    'bcrypt',
]

missing = []

for package in required_packages:
    try:
        if package == 'mysql.connector':
            __import__('mysql.connector')
        elif package == 'pydantic_settings':
            __import__('pydantic_settings')
        else:
            __import__(package)
        print(f"✓ {package}")
    except ImportError:
        print(f"✗ {package} - НЕ УСТАНОВЛЕН")
        missing.append(package)

print("="*60)

if missing:
    print(f"\n❌ Не хватает пакетов: {', '.join(missing)}")
    print("\nУстановите зависимости командой:")
    print("   pip install -r requirements.txt")
    print("\nИЛИ если пакеты установлены в другом окружении Python:")
    print("   python -m pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\n✅ Все пакеты установлены!")
    print("\nЗапуск сервера...")
    print("="*60)
    
    # Запускаем main.py
    try:
        import main
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

