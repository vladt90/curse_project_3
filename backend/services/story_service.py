"""
ИИ-экскурсовод: генерация и кэширование рассказов об объектах
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from config import settings
from database import get_db_cursor


def ensure_story_table() -> None:
    """
    Создать таблицу кэша, если её ещё нет (чтобы не требовать ручных миграций).
    """
    with get_db_cursor(dictionary=False) as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS object_stories (
                object_id INT PRIMARY KEY,
                model VARCHAR(200) NOT NULL,
                story TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (object_id) REFERENCES heritage_objects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )


def get_cached_story(object_id: int, model: str) -> Optional[str]:
    ensure_story_table()
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT story
            FROM object_stories
            WHERE object_id = %s AND model = %s
            """,
            (object_id, model),
        )
        row = cursor.fetchone()
        return row["story"] if row else None


def save_story(object_id: int, model: str, story: str) -> None:
    ensure_story_table()
    with get_db_cursor(dictionary=False) as cursor:
        cursor.execute(
            """
            INSERT INTO object_stories (object_id, model, story)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                model = VALUES(model),
                story = VALUES(story),
                updated_at = CURRENT_TIMESTAMP
            """,
            (object_id, model, story),
        )


def get_object_data(object_id: int) -> Optional[Dict]:
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
            (object_id,),
        )
        return cursor.fetchone()


def build_fallback_story(obj: Dict) -> str:
    """
    Бесплатный fallback (без LLM): короткий текст из имеющихся полей.
    """
    def count_sentences(text: str) -> int:
        # Простой счетчик предложений (достаточно для fallback-текста)
        return sum(1 for ch in text if ch in ".!?")

    def add_sentence(parts_list, sentence: str, max_sentences: int = 8) -> None:
        if not sentence:
            return
        current = " ".join(parts_list)
        if count_sentences(current) >= max_sentences:
            return
        if sentence[-1] not in ".!?":
            sentence = sentence + "."
        parts_list.append(sentence)

    parts = []
    name = obj.get("name") or "Объект культурного наследия"
    add_sentence(parts, f"Вы сейчас у объекта «{name}».")

    address = obj.get("address")
    if address:
        add_sentence(parts, f"Адрес: {address}")

    ot = obj.get("object_type")
    if ot:
        add_sentence(parts, f"Тип: {ot}")

    year = obj.get("build_year")
    if year:
        add_sentence(parts, f"Год постройки: {year}")

    district = obj.get("district")
    if district:
        add_sentence(parts, f"Район: {district}")

    adm_area = obj.get("adm_area")
    if adm_area:
        add_sentence(parts, f"Округ: {adm_area}")

    category = obj.get("category")
    if category:
        add_sentence(parts, f"Категория: {category}")

    sec = obj.get("security_status")
    if sec:
        add_sentence(parts, f"Статус охраны: {sec}")

    descr = obj.get("description")
    if descr:
        short = descr.strip()
        if len(short) > 360:
            short = short[:360].rsplit(" ", 1)[0] + "…"
        # Если описание длинное и содержит несколько предложений — добавим целиком (но общий лимит 8 предложений сохранится)
        add_sentence(parts, short)

    # Добиваем до 5–8 предложений без одинаковой концовки на всех объектах (детерминированно выбираем фразу).
    tips = [
        "Посмотрите, как объект «сидит» в улице: масштаб, линия фасада и ракурс часто многое объясняют без лишних слов.",
        "Обратите внимание на ритм окон и декоративные элементы: по ним нередко считывается эпоха и назначение здания.",
        "Пройдитесь вокруг: разные стороны фасада обычно раскрывают объект лучше, чем взгляд с одной точки.",
        "Если есть возможность, сравните материалы и фактуру: камень, штукатурка и металл дают подсказки о времени постройки.",
    ]
    oid = str(obj.get("id") or obj.get("global_id") or name)
    idx = hashlib.sha256(oid.encode("utf-8")).digest()[0] % len(tips)
    # Добавляем tip, только если не вылезаем за 8 предложений и нужно добрать длину
    if count_sentences(" ".join(parts)) < 5:
        add_sentence(parts, tips[idx])

    return " ".join(parts)


def generate_story_openrouter(obj: Dict) -> str:
    """
    Генерация текста через OpenRouter Chat Completions API.
    """
    if not settings.OPENROUTER_API_KEY:
        return build_fallback_story(obj)

    prompt = (
        "Ты — ИИ-экскурсовод по Москве. Сгенерируй небольшой рассказ (5–8 предложений) на русском языке "
        "про объект культурного наследия. Представь, что человек УЖЕ стоит рядом с объектом (никаких «если будете рядом»). "
        "Используй ТОЛЬКО данные из контекста. Не выдумывай факты (архитектор, события, даты), если их нет в контексте. "
        "Тон: дружелюбный, без пафоса. Без списков. Не заканчивай универсальными советами — финал должен опираться на контекст.\n\n"
        f"Контекст:\n"
        f"Название: {obj.get('name')}\n"
        f"Адрес: {obj.get('address')}\n"
        f"Район: {obj.get('district')}\n"
        f"Округ: {obj.get('adm_area')}\n"
        f"Тип: {obj.get('object_type')}\n"
        f"Категория: {obj.get('category')}\n"
        f"Статус охраны: {obj.get('security_status')}\n"
        f"Год постройки: {obj.get('build_year')}\n"
        f"Описание: {obj.get('description')}\n"
    )

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты полезный помощник."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 420,
    }

    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    data = json.dumps(payload).encode("utf-8")

    req = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost",
            "X-Title": settings.APP_NAME,
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=25) as resp:
            resp_json = json.load(resp)
    except (HTTPError, URLError, TimeoutError) as exc:
        # Не валим фичу: отдаем fallback
        return build_fallback_story(obj)

    try:
        content = resp_json["choices"][0]["message"]["content"].strip()
        return content or build_fallback_story(obj)
    except Exception:
        return build_fallback_story(obj)


def get_story_for_object(object_id: int) -> str:
    obj = get_object_data(object_id)
    if not obj:
        return ""

    # Ключ кэша должен зависеть от режима (LLM vs fallback), иначе при добавлении ключа OpenRouter
    # можно "залипнуть" на старом fallback-тексте и никогда не перейти на ИИ.
    if settings.OPENROUTER_API_KEY:
        cache_key = f"{settings.OPENROUTER_MODEL}:prompt-v3"
    else:
        cache_key = "fallback:story-v3"

    cached = get_cached_story(object_id, cache_key)
    if cached:
        return cached

    story = generate_story_openrouter(obj)
    if story:
        save_story(object_id, cache_key, story)
    return story

