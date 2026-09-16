"""
Модуль main.py

Точка входа в бота. Запускает polling и инициализирует базу данных.
"""
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

from config import BOT_TOKEN, GROUP_ID, TEST_MODE, ADMIN_IDS

from db import init_db

from handlers import admin, user

from keyboards import get_main_menu

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем роутеры
dp.include_router(admin.router)
dp.include_router(user.router)

# Инициализация базы при старте
init_db()


@dp.message(CommandStart())
async def start(message: types.Message):
    """/start — приветствие. Админам показываем меню, остальным — просто текст."""
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n"
            "Я бот для организации спортивных событий.\n\n"
            "Используйте кнопки ниже:",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n"
            "Я бот для организации спортивных событий.\n\n"
            "Следи за анонсами в группе и нажимай «✅ Я в деле», чтобы записаться."
        )


async def main():
    # Логируем режим работы при старте
    mode = "ТЕСТ" if TEST_MODE else "ПРОД"
    logger.info(f"=== Бот запускается в режиме: {mode} ===")
    logger.info(f"=== GROUP_ID: {GROUP_ID} ===")
    logger.info(f"=== Админы: {ADMIN_IDS} ===")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
