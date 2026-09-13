"""
Модуль config.py

Загружает переменные окружения из файла .env.
Содержит токен бота, список админов и ID групп.
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

# Список групп
GROUP_IDS = [
    int(os.getenv("GROUP_ID", 0)),
    int(os.getenv("GROUP_ID_2", 0)),
]

# Убираем нули
ADMIN_IDS = [admin_id for admin_id in ADMIN_IDS if admin_id != 0]
GROUP_IDS = [group_id for group_id in GROUP_IDS if group_id != 0]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env!")
