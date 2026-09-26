"""
Модуль config.py

Загружает переменные окружения из файла .env.
Поддерживает переключение между тестовой и рабочей группами
через флаг TEST_MODE.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# РЕЖИМ: тест или прод
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# ============================================================
# БОТ
# ============================================================
if TEST_MODE:
    BOT_TOKEN = os.getenv("BOT_TOKEN_TEST")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN_TEST не задан в .env.")
else:
    BOT_TOKEN = os.getenv("BOT_TOKEN_PROD")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN_PROD не задан в .env.")

# ============================================================
# АДМИНЫ
# ============================================================
ADMIN_IDS = [
    admin_id for admin_id in [
        int(os.getenv("ADMIN_ID", 0) or 0),
        int(os.getenv("ADMIN_ID_2", 0) or 0),
    ]
    if admin_id != 0
]
if not ADMIN_IDS:
    raise ValueError(
        "Не задан ни один админ. "
        "Добавь в .env: ADMIN_ID=123456789 (и опционально ADMIN_ID_2=...)"
    )

# ============================================================
# ГРУППА И ТОПИКИ
# ============================================================
if TEST_MODE:
    GROUP_ID = int(os.getenv("GROUP_ID_TEST", 0) or 0)
    if not GROUP_ID:
        raise ValueError("TEST_MODE=true, но GROUP_ID_TEST не задан в .env.")

    TOPICS = {
        "general":     {"name": "📢 General",     "thread_id": None},
        "trainings":   {"name": "🏐 Тренировки",  "thread_id": int(os.getenv("TOPIC_TRAININGS_TEST", 2) or 2)},
        "photo_video": {"name": "📸 Фото/видео",  "thread_id": int(os.getenv("TOPIC_PHOTO_VIDEO_TEST", 3) or 3)},
        "flood":       {"name": "💬 Флудилка",    "thread_id": int(os.getenv("TOPIC_FLOOD_TEST", 4) or 4)},
        "camps":       {"name": "🏕 Кемпы",       "thread_id": int(os.getenv("TOPIC_CAMPS_TEST", 5) or 5)},
    }
else:
    GROUP_ID = int(os.getenv("GROUP_ID_PROD", 0) or 0)
    if not GROUP_ID:
        raise ValueError("TEST_MODE=false, но GROUP_ID_PROD не задан в .env.")

    TOPICS = {
        "general":     {"name": "📢 General",           "thread_id": None},
        "trainings":   {"name": "🏐 Тренировки",        "thread_id": int(os.getenv("TOPIC_TRAININGS", 4357) or 4357)},
        "photo_video": {"name": "📸 Фото/видео",        "thread_id": int(os.getenv("TOPIC_PHOTO_VIDEO", 4358) or 4358)},
        "flood":       {"name": "💬 Флудилка",          "thread_id": int(os.getenv("TOPIC_FLOOD", 4359) or 4359)},
        "camps":       {"name": "🏕 Кемпы и турниры",   "thread_id": int(os.getenv("TOPIC_CAMPS", 4559) or 4559)},
    }
