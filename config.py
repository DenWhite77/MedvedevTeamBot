"""
Модуль config.py

Загружает переменные окружения из файла .env.
Содержит токен бота и ID администратора/группы.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GROUP_ID = int(os.getenv("GROUP_ID", 0))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env!")
