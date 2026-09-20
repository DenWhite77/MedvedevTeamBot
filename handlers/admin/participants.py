"""
Модуль handlers/admin/participants.py

Содержит обработчики для работы с участниками:
- Список участников события
- Выписка участника
- Подтверждение оплаты (переход в основной состав)
- Отклонение оплаты (выписка)
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, LinkPreviewOptions
from aiogram import Bot

from config import GROUP_ID

from db import (
    get_event, get_event_message_id, get_participants,
    remove_participant, confirm_payment,
)

from keyboards import (
    get_event_keyboard, get_admin_list_keyboard,
)

from .common import is_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_participants")


# ============================================================
# СПИСОК УЧАСТНИКОВ
# ============================================================

@router.callback_query(F.data.startswith("list_"))
async def list_participants(callback: CallbackQuery, bot: Bot):
    """Показывает админу список участников с кнопками выписки."""
    event_id = int(callback.data.split("_")[1])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    participants = get_participants(event_id)
    if not participants:
        await callback.answer("⚠️ Пока никто не записался.", show_alert=True)
        return

    await callback.message.answer(
        f"📋 *Список участников события:*\n"
        f"📅 {event[1]}\n\n"
        f"Нажмите «❌ Выписать», чтобы удалить участника.",
        parse_mode="Markdown",
        reply_markup=get_admin_list_keyboard(event_id, participants)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_"))
async def remove_participant_handler(callback: CallbackQuery, bot: Bot):
    """Админ выписывает участника."""
    parts = callback.data.split("_")
    event_id = int(parts[1])
    user_id = int(parts[2])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    remove_participant(event_id, user_id)
    await callback.answer("✅ Участник выписан.")

    logger.info(f"Админ выписал участника: event_id={event_id}, user_id={user_id}")

    # Обновляем сообщение в группе
    from handlers.user import format_event_message
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
            logger.warning(f"Не удалось отредактировать сообщение: {e}")

    # Обновляем список в личке админа
    try:
        await callback.message.edit_text(
            text=(
                f"📋 *Список участников события:*\n"
                f"📅 {event[1]}\n\n"
                f"Нажмите «❌ Выписать», чтобы удалить участника."
            ),
            parse_mode="Markdown",
            reply_markup=get_admin_list_keyboard(event_id, participants)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить список: {e}")


# ============================================================
# ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ ОПЛАТЫ
# ============================================================

@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: CallbackQuery, bot: Bot):
    """Админ подтверждает оплату — участник переходит в основной состав."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    confirm_payment(event_id, user_id)
    await callback.answer("✅ Оплата подтверждена!")

    logger.info(f"Админ подтвердил оплату: event_id={event_id}, user_id={user_id}")

    # Обновляем сообщение в группе
    from handlers.user import format_event_message
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
            logger.warning(f"Не удалось отредактировать сообщение: {e}")


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment_handler(callback: CallbackQuery, bot: Bot):
    """Админ отклоняет оплату — участник выписывается."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    remove_participant(event_id, user_id)
    await callback.answer("❌ Участник выписан.")

    logger.info(f"Админ отклонил оплату: event_id={event_id}, user_id={user_id}")

    # Обновляем сообщение в группе
    from handlers.user import format_event_message
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
            logger.warning(f"Не удалось обновить сообщение: {e}")

    await callback.message.answer("❌ Участник выписан из события.")
