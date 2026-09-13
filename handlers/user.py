"""
Модуль handlers/user.py

Содержит обработчики для участников:
- Запись на событие (кнопка «Я в деле»)
- Отмена записи
- Отметка «Оплатил»
"""
import logging
from aiogram import Router, types, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import get_event, add_participant, get_participants, remove_participant
from keyboards import get_event_keyboard

logger = logging.getLogger(__name__)

# Роутер для участников
router = Router()


def format_event_message(event, participants):
    """Формирует текст сообщения с событием и списком участников."""
    event_id = event[0]
    direction = event[1]
    place = event[3]
    date = event[4]
    time = event[5]
    max_participants = event[6]
    price = event[7]
    payment_info = event[8]
    comment = event[9] or "—"

    # Разделяем участников на основной состав и резерв
    main_list = []
    reserve_list = []

    for p in participants:
        # p = (user_id, username, full_name, status, paid)
        user_id, username, full_name, status, paid = p
        name = full_name or username or f"id{user_id}"

        if status == "main":
            main_list.append(f"✅ {name}")
        else:
            reserve_list.append(f"🕐 {name}")

    text = (
        f"📅 *{direction}*\n\n"
        f"📍 *Место:* {place}\n"
        f"📅 *Дата:* {date}\n"
        f"🕐 *Время:* {time}\n"
        f"👥 *Макс. участников:* {max_participants}\n"
        f"💰 *Стоимость:* {price} ₽\n"
        f"💳 *Оплата:* {payment_info}\n"
        f"📝 *Комментарий:* {comment}\n\n"
    )

    if main_list:
        text += f"*Основной состав ({len(main_list)}):*\n" + "\n".join(main_list) + "\n\n"

    if reserve_list:
        text += f"*Резерв ({len(reserve_list)}):*\n" + "\n".join(reserve_list) + "\n\n"

    if not main_list and not reserve_list:
        text += "_Пока никто не записался._\n\n"

    text += "Нажмите «✅ Я в деле», чтобы записаться!"

    return text


@router.callback_query(F.data.startswith("join_"))
async def join_event(callback: CallbackQuery, bot: Bot):
    """Запись участника на событие."""
    # Получаем event_id из callback_data
    event_id = int(callback.data.split("_")[1])

    # Проверяем, что событие существует
    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    # Добавляем участника в резерв
    user = callback.from_user
    success = add_participant(
        event_id=event_id,
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or ""
    )

    if not success:
        await callback.answer("⚠️ Ты уже записан на это событие!", show_alert=True)
        return

    # Отвечаем участнику
    await callback.answer("✅ Ты записан в резерв!")

    # Отправляем личное сообщение участнику
    try:
        await bot.send_message(
            chat_id=user.id,
            text=(
                f"✅ Ты записан на событие *{event[1]}*!\n\n"
                f"📅 {event[4]} в {event[5]}\n"
                f"📍 {event[3]}\n"
                f"💰 Стоимость: {event[7]} ₽\n\n"
                f"После оплаты нажми «💳 Оплатил» в сообщении группы."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить ЛС пользователю {user.id}: {e}")

    # Обновляем сообщение в группе
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)

    try:
        await callback.message.edit_text(
            text=new_text,
            parse_mode="Markdown",
            reply_markup=get_event_keyboard(event_id)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")
