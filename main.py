"""
Модуль main.py

Точка входа в бота. Запускает polling и инициализирует базу данных.
"""
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from db import init_db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы при старте
init_db()


@dp.message(types.Message)
async def start(message: types.Message):
    if message.text == "/start":
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n"
            "Я бот для организации спортивных событий.\n"
            "Скоро здесь появятся команды для создания событий и записи."
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
