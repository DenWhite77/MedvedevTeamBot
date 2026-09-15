"""
Модуль config.py

Загружает переменные окружения из файла .env.
Поддерживает переключение между тестовой и рабочей группами.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список админов
ADMIN_IDS = [
    int(os.getenv("ADMIN_ID", 0)),
    int(os.getenv("ADMIN_ID_2", 0)),
]
ADMIN_IDS = [admin_id for admin_id in ADMIN_IDS if admin_id != 0]

# ============================================================
# РЕЖИМ: тест или прод
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# Сначала определяем значения по умолчанию
GROUP_ID = 0
TOPICS = {}

if TEST_MODE:
    GROUP_ID = int(os.getenv("GROUP_ID_TEST", 0))
    TOPICS = {
        "general": {"name": "📢 General", "thread_id": None},
        "trainings": {"name": "🏐 Тренировки", "thread_id": 2},
        "photo_video": {"name": "📸 Фото/видео", "thread_id": 3},
        "flood": {"name": "💬 Флудилка", "thread_id": 4},
        "camps": {"name": "🏕 Кемпы", "thread_id": 5},
    }
else:
    GROUP_ID = int(os.getenv("GROUP_ID", 0))
    TOPICS = {
        "general": {"name": "📢 General", "thread_id": None},
        "trainings": {"name": "🏐 Тренировки", "thread_id": 4357},
        "photo_video": {"name": "📸 Фото/видео", "thread_id": 4358},
        "flood": {"name": "💬 Флудилка", "thread_id": 4359},
        "camps": {"name": "🏕 Кемпы и турниры", "thread_id": 4559},
    }
