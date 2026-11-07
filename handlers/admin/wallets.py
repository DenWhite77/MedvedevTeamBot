import logging
import sqlite3
from aiogram import Router, F, Bot, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards import get_admin_wallet_management_keyboard, get_cancel_keyboard
from db import get_connection

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

# Инициализируем роутер кошельков
router = Router()

# Состояния для управления кошельками
class WalletStates(StatesGroup):
    waiting_for_user_identifier = State()
    waiting_for_amount = State()
    processing = State()        # Ожидание суммы пополнения


# ============================================================
# УПРАВЛЕНИЕ ДЕПОЗИТАМИ (АДМИНКА)
# ============================================================

@router.callback_query(F.data == "admin_manage_wallets")
async def admin_wallet_menu(callback: types.CallbackQuery):
    """Открывает меню управления кошельками для Леры."""
    await callback.message.edit_text(
        "<b>💰 Управление депозитами участников</b>\n\n"
        "Здесь вы можете зачислить предоплату от игроков, списать средства вручную "
        "или посмотреть ведомость по всем балансам.",
        parse_mode="HTML",
        reply_markup=get_admin_wallet_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_list_wallets")
async def admin_list_all_wallets(callback: types.CallbackQuery):
    """Выводит список всех пользователей с положительным балансом."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, full_name, balance 
                FROM user_wallets 
                WHERE balance != 0 
                ORDER BY balance DESC;
            """)
            wallets = cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении списка кошельков: {e}")
        await callback.answer("❌ Ошибка при обращении к БД", show_alert=True)
        return

    if not wallets:
        text = "<b>📋 Ведомость депозитов:</b>\n\nАктивных депозитов в системе пока нет."
    else:
        text = "<b>📋 Список активных депозитов участников:</b>\n\n"
        total_sum = 0.0
        for idx, (u_id, username, f_name, balance) in enumerate(wallets, 1):
            name = f_name or username or f"ID: {u_id}"
            user_ref = f"@{username}" if username else f"<code>{u_id}</code>"
            text += f"{idx}. {name} ({user_ref}) — <b>{balance:,.2f} руб.</b>\n"
            total_sum += balance
        text += f"\n💰 <b>Всего на депозитах в клубе:</b> {total_sum:,.2f} руб."

    # Кнопка возврата в меню кошельков
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_wallets")]
    ])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin_deposit_money")
async def admin_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    """Шаг 1: Просим админа прислать ID/Юзернейм или переслать сообщение игрока."""
    await callback.message.edit_text(
        "<b>➕ Изменение баланса</b>\n\n"
        "Перешлите мне любое сообщение от игрока, которому хотите изменить баланс, "
        "или просто введите его <b>Telegram ID</b> (число) / <b>@username</b>:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WalletStates.waiting_for_user_identifier)
    await callback.answer()


@router.message(WalletStates.waiting_for_user_identifier)
async def admin_deposit_get_user(message: types.Message, state: FSMContext):
    """Шаг 2: Идентифицируем пользователя."""
    target_user_id = None
    username_input = None

    # Если сообщение переслано
    if message.forward_from:
        target_user_id = message.forward_from.id
    else:
        text = message.text.strip()
        if text.isdigit():
            target_user_id = int(text)
        elif text.startswith("@"):
            username_input = text.replace("@", "")
        else:
            await message.answer("❌ Неверный формат. Введите числовой ID, @username или перешлите сообщение.")
            return

    # Ищем пользователя в нашей системе, чтобы подтвердить Лере, кого она пополняет
    found_user = None
    with get_connection() as conn:
        cursor = conn.cursor()
        if target_user_id:
            cursor.execute("SELECT user_id, username, full_name FROM user_wallets WHERE user_id = ?", (target_user_id,))
            found_user = cursor.fetchone()
            if not found_user:
                cursor.execute("SELECT user_id, username, full_name FROM participants WHERE user_id = ? LIMIT 1",
                               (target_user_id,))
                found_user = cursor.fetchone()
        elif username_input:
            cursor.execute("SELECT user_id, username, full_name FROM user_wallets WHERE LOWER(username) = LOWER(?)",
                           (username_input,))
            found_user = cursor.fetchone()
            if not found_user:
                cursor.execute(
                    "SELECT user_id, username, full_name FROM participants WHERE LOWER(username) = LOWER(?) LIMIT 1",
                    (username_input,))
                found_user = cursor.fetchone()

    if not found_user:
        if username_input:
            await message.answer(
                f"❌ Пользователь @{username_input} не найден в базе бота. Он должен хотя бы раз запустить бота или записаться на игру.")
            await state.clear()
            return
        else:
            target_user_id = target_user_id
            name_to_show = f"ID: {target_user_id}"
    else:
        target_user_id, db_username, db_full_name = found_user
        name_to_show = db_full_name or db_username or f"ID: {target_user_id}"

    await state.update_data(target_user_id=target_user_id, name_to_show=name_to_show)
    await message.answer(
        f"👤 Выбран игрок: <b>{name_to_show}</b> (ID: <code>{target_user_id}</code>)\n\n"
        f"Введите сумму пополнения.\n"
        f"<i>Пример: 15000 (чтобы начислить) или -1500 (чтобы списать вручную):</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WalletStates.waiting_for_amount)


@router.message(WalletStates.waiting_for_amount)
async def admin_deposit_confirm(message: types.Message, state: FSMContext, bot: Bot):
    """Шаг 3: Проводим транзакцию, обновляем БД и уведомляем обе стороны."""
    # Защита от двойного нажатия
    current_state = await state.get_state()
    if current_state == WalletStates.processing:
        await message.answer("⏳ Транзакция уже обрабатывается, подождите...")
        return

    try:
        amount = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число. Пример: 15000 или 500.50")
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    name_to_show = data["name_to_show"]

    # Ставим флаг «в процессе»
    await state.set_state(WalletStates.processing)

    tx_type = "deposit" if amount >= 0 else "expense"
    comment = "Пополнение администратором" if amount >= 0 else "Ручное списание администратором"

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (target_user_id,))
            row = cursor.fetchone()

            if row is None:
                current_balance = amount
                cursor.execute("""
                    INSERT INTO user_wallets (user_id, username, full_name, balance)
                    VALUES (?, ?, ?, ?)
                """, (target_user_id,
                      message.from_user.username if target_user_id == message.from_user.id else None,
                      name_to_show, current_balance))
            else:
                current_balance = row[0] + amount
                cursor.execute("""
                    UPDATE user_wallets 
                    SET balance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (current_balance, target_user_id))

            cursor.execute("""
                INSERT INTO wallet_transactions (user_id, amount, type, comment)
                VALUES (?, ?, ?, ?)
            """, (target_user_id, amount, tx_type, comment))

            conn.commit()

    except Exception as e:
        logger.error(f"Ошибка при проведении транзакции админом: {e}")
        await message.answer("❌ Произошла ошибка базы данных при сохранении баланса.")
        await state.clear()
        return

    sign = "➕ Начислено" if amount >= 0 else "➖ Списано"
    await message.answer(
        f"✅ <b>Операция успешна!</b>\n\n"
        f"👤 Игрок: {name_to_show}\n"
        f"📊 {sign}: {amount:,.2f} руб.\n"
        f"💰 Текущий баланс игрока: <b>{current_balance:,.2f} руб.</b>",
        parse_mode="HTML"
    )

    try:
        if amount >= 0:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"💰 <b>Баланс вашего кошелька пополнен!</b>\n\n"
                     f"➕ Зачислено: <b>{amount:,.2f} руб.</b>\n"
                     f"💳 Текущий остаток: <b>{current_balance:,.2f} руб.</b>\n\n"
                     f"<i>Теперь вы можете оплачивать игры и места для друзей моментально прямо из кошелька!</i>",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"📉 <b>Списание с кошелька</b>\n\n"
                     f"➖ Списано администратором: <b>{abs(amount):,.2f} руб.</b>\n"
                     f"💳 Текущий остаток: <b>{current_balance:,.2f} руб.</b>",
                parse_mode="HTML"
            )
    except Exception as notify_err:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {notify_err}")

    # Сбрасываем состояние (флаг «в процессе»)
    await state.clear()
