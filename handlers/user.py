"""
Модуль handlers/user.py

Содержит обработчики для участников:
- Запись на событие (кнопка «Я в деле»)
- Отмена записи
- Отметка «Оплатил»
"""
import logging
from urllib.parse import quote

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LinkPreviewOptions

from config import ADMIN_IDS, GROUP_ID

from db import (
    get_event, get_event_message_id, add_participant, get_participants,
    remove_participant, mark_paid,
)

from keyboards import get_event_keyboard
from keyboards import get_payment_confirm_keyboard

logger = logging.getLogger(__name__)

router = Router(name="user")


def format_event_message(event, participants):
    """Формирует текст сообщения с событием и списком участников."""
    direction = event[1]
    place = event[3]
    date = event[4]
    time = event[5]
    max_participants = event[6]
    price = event[7]
    payment_info = event[8]
    comment = event[9] or "—"

    # Ссылка на Яндекс.Карты (всегда в тексте события)
    yandex_link = f"\n🗺 [Открыть на Яндекс.Картах](https://yandex.ru/maps/?text={quote(place)})"

    main_list = []
    reserve_list = []

    for p in participants:
        user_id, username, full_name, status, paid = p
        name = full_name or username or f"id{user_id}"
        marker = " 💳" if paid else ""

        if status == "main":
            main_list.append(f"✅ {name}{marker}")
        else:
            reserve_list.append(f"🕐 {name}{marker}")

    text = (
        f"📅 *{direction}*\n\n"
        f"📍 *Место:* {place}\n"
        f"📅 *Дата:* {date}\n"
        f"🕐 *Время:* {time}\n"
        f"👥 *Макс. участников:* {max_participants}\n"
        f"💰 *Стоимость:* {price} ₽\n"
        f"💳 *Оплата:* {payment_info}\n"
        f"📝 *Комментарий:* {comment}"
        f"{yandex_link}\n\n"
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
    event_id = int(callback.data.split("_")[1])

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    user = callback.from_user
    success = add_participant(
        event_id=event_id,
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or ""
    )

    if not success:
        logger.info(f"User {user.id} not added to event {event_id} (already registered).")
        await callback.answer("⚠️ Вы уже записаны на это событие!", show_alert=True)
        return

    logger.info(f"User {user.id} registered for event {event_id}.")

    await callback.answer("✅ Вы записаны в резерв!")

    try:
        await bot.send_message(
            chat_id=user.id,
            text=(
                f"✅ Вы записаны на событие *{event[1]}*!\n\n"
                f"📅 {event[4]} в {event[5]}\n"
                f"📍 {event[3]}\n"
                f"💰 Стоимость: {event[7]} ₽\n\n"
                f"После оплаты нажмите «💳 Оплатил» в сообщении группы."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Cannot send DM to {user.id}: {e}")

    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message: {e}")


@router.callback_query(F.data.startswith("paid_"))
async def paid_event(callback: CallbackQuery, bot: Bot):
    """Участник сообщает, что оплатил."""
    event_id = int(callback.data.split("_")[1])

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    participants = get_participants(event_id)
    user_ids = [p[0] for p in participants]

    user = callback.from_user
    if user.id not in user_ids:
        await callback.answer(
            "⚠️ Сначала нажмите «✅ Я в деле», чтобы записаться!",
            show_alert=True
        )
        return

    mark_paid(event_id, user.id)
    await callback.answer("✅ Спасибо! Админ проверит оплату.")

    logger.info(f"User {user.id} marked paid for event {event_id}.")

    # Обновляем сообщение в группе
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message after paid: {e}")

    # Уведомление всем админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💳 *{user.full_name}* сообщил, что оплатил:\n\n"
                    f"📅 *{event[1]}*\n"
                    f"💰 Стоимость: {event[7]} ₽\n"
                    f"📍 {event[3]}\n"
                    f"📅 {event[4]} в {event[5]}\n\n"
                    f"Подтвердить оплату?"
                ),
                parse_mode="Markdown",
                reply_markup=get_payment_confirm_keyboard(event_id, user.id)
            )
        except Exception as e:
            logger.warning(f"Cannot notify admin {admin_id}: {e}")


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_event(callback: CallbackQuery, bot: Bot):
    """Отмена записи участником."""
    event_id = int(callback.data.split("_")[1])

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    user = callback.from_user
    participants = get_participants(event_id)
    user_ids = [p[0] for p in participants]

    if user.id not in user_ids:
        await callback.answer("⚠️ Вы не записаны на это событие.", show_alert=True)
        return

    remove_participant(event_id, user.id)
    await callback.answer("✅ Вы отменили запись.")

    logger.info(f"User {user.id} cancelled registration for event {event_id}.")

    try:
        await bot.send_message(
            chat_id=user.id,
            text=(
                f"❌ Вы отменили запись на событие *{event[1]}*.\n\n"
                f"📅 {event[4]} в {event[5]}\n"
                f"📍 {event[3]}"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Cannot send DM: {e}")

    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message: {e}")
