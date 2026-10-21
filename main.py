"""
Модуль main.py

Точка входа в бота. Запускает polling и инициализирует базу данных.
"""
import logging
import asyncio
import sys
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand, BotCommandScopeDefault, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, GROUP_ID, TEST_MODE, ADMIN_IDS
from db import init_db
from handlers import admin, user
from keyboards import get_main_menu

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализируем диспетчер глобально
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):
    """/start — приветствие. Админам показываем меню, остальным — просто текст."""
    user_id = message.from_user.id
    logger.info(f"Получена команда /start от пользователя {user_id}")

    try:
        admin_ids_ints = [int(x) for x in ADMIN_IDS]
    except (ValueError, TypeError):
        admin_ids_ints = ADMIN_IDS

    if user_id == 1179262985 or user_id in admin_ids_ints:
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n"
            "Я бот для организации спортивных событий.\n\n"
            "Используйте кнопки ниже:",
            reply_markup=get_main_menu()
        )
    else:
        logger.info(f"Отказ в доступе к меню. Юзер ID: {user_id}. Список админов: {ADMIN_IDS}")
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n"
            "Я бот для организации спортивных событий.\n\n"
            "Следи за анонсами в группе и нажимай «✅ Я в деле», чтобы записаться."
        )


# ============================================================
# ДОРАБОТКА АДМИНКИ: ОБХОД ЗАГЛУШКИ «В РАЗРАБОТКЕ»
# ============================================================
@dp.callback_query(F.data == "admin_manage_lists")
async def admin_edit_events_list(callback: types.CallbackQuery):
    """Выводит реальный список событий для управления списками участников."""
    user_id = callback.from_user.id

    try:
        admin_ids_ints = [int(x) for x in ADMIN_IDS]
    except (ValueError, TypeError):
        admin_ids_ints = ADMIN_IDS

    if user_id != 1179262985 and user_id not in admin_ids_ints:
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    # Вытаскиваем все активные события из базы данных
    events = []
    try:
        with sqlite3.connect("events.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, date, time FROM events WHERE status = 'active' ORDER BY id DESC;")
            events = cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при чтении событий для админки: {e}")

    if not events:
        await callback.message.edit_text("📭 Активных событий в базе пока нет. Создайте событие кнопкой выше!")
        await callback.answer()
        return

    # Строим клавиатуру со списком событий
    buttons = []
    for ev in events:
        ev_id, title, date, time = ev
        btn_text = f"🔹 ID {ev_id}: {title} ({date})"
        if len(btn_text) > 40:
            btn_text = btn_text[:37] + "..."

        # Запрос перенаправляется на обработчик list_participants в participants.py
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"list_{ev_id}")])

    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")])
    events_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        "<b>🛠 Управление списками участников</b>\n\n"
        "Выберите спортивное событие ниже, чтобы переводить участников "
        "между основным и запасным составом, или удалять их:",
        parse_mode="HTML",
        reply_markup=events_kb
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery):
    """Возвращает админа из списка событий назад в Главное меню."""
    await callback.message.edit_text(
        f"Привет, {callback.from_user.full_name}!\n"
        "Я бот для организации спортивных событий.\n\n"
        "Используйте кнопки ниже:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============================================================
# ВОССТАНОВЛЕННАЯ ФУНКЦИЯ НАСТРОЙКИ СИНЕЙ КНОПКИ
# ============================================================
async def setup_bot_commands(bot: Bot):
    """Регистрирует кнопку Меню в левом нижнем углу интерфейса Telegram."""
    try:
        commands = [
            BotCommand(command="start", description="🚀 Главное меню")
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Кнопка 'Меню' успешно зарегистрирована в Telegram.")
    except Exception as e:
        logger.error(f"Не удалось зарегистрировать кнопку команд: {e}")


@dp.startup()
async def on_startup(bot: Bot):
    """Выполняется строго в момент запуска поллинга, когда асинхронный цикл уже активен."""
    logger.info("--- Запуск стартовых процедур бота ---")
    logger.info("Инициализация базы данных...")
    try:
        init_db()
    except Exception as db_err:
        logger.error(f"Ошибка при инициализации БД: {db_err}", exc_info=True)
    logger.info("--- Все стартовые процедуры выполнены успешно ---")


async def main():
    mode = "ТЕСТ" if TEST_MODE else "ПРОД"
    logger.info(f"=== Конфигурация: Режим: {mode} | GROUP_ID: {GROUP_ID} ===")

    logger.info("Регистрация роутеров...")
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Настройка прокси строки
    bot_proxy = None
    if TEST_MODE:
        bot_proxy = "http://127.0.0.1:10809"
        logger.info(f"Локальный тест: Будет использован прокси Happ {bot_proxy}")

    logger.info("Создание объекта Bot...")
    bot = Bot(token=BOT_TOKEN, proxy=bot_proxy)

    logger.info("Настройка команд интерфейса Telegram...")
    await setup_bot_commands(bot)

    logger.info("=== СТАРТ ПОЛЛИНГА (Бот начинает слушать Telegram) ===")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка во время polling: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    print("--- Запуск скрипта через asyncio.run(main()) ---")
    try:
        asyncio.run(main())
    except Exception as global_err:
        print(f"ГЛОБАЛЬНАЯ ОШИБКА ИНТЕРПРЕТАТОРА: {global_err}")
