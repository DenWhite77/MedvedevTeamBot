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
    add_to_main, move_to_reserve,
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
        f"📋 <b>Список участников события:</b>\n"
        f"📅 {event[1]}\n\n"
        f"Нажмите «❌ Выписать», чтобы удалить участника.",
        parse_mode="HTML",
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
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")

    # Обновляем список в личке админа
    try:
        await callback.message.edit_text(
            text=(
                f"📋 <b>Список участников события:</b>\n"
                f"📅 {event[1]}\n\n"
                f"Нажмите «❌ Выписать», чтобы удалить участника."
            ),
            parse_mode="HTML",
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
                parse_mode="HTML",
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
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Не удалось обновить сообщение: {e}")

    await callback.message.answer("❌ Участник выписан из события.")


# ============================================================
# ПЕРЕВОД В ОСНОВНОЙ / ЗАПАСНОЙ
# ============================================================

@router.callback_query(F.data.startswith("to_main_"))
async def to_main_handler(callback: CallbackQuery, bot: Bot):
    """Переводит участника из запасного в основной."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    add_to_main(event_id, user_id)
    await callback.answer("🟢 Переведён в основной состав.")

    logger.info(f"Админ перевёл в основной: event_id={event_id}, user_id={user_id}")

    await _refresh_participants_message(callback, bot, event_id)


@router.callback_query(F.data.startswith("to_reserve_"))
async def to_reserve_handler(callback: CallbackQuery, bot: Bot):
    """Переводит участника из основного в запасной."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    move_to_reserve(event_id, user_id)
    await callback.answer("🟡 Переведён в запасной состав.")

    logger.info(f"Админ перевёл в запасной: event_id={event_id}, user_id={user_id}")

    await _refresh_participants_message(callback, bot, event_id)


# ============================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ (обновление сообщений)
# ============================================================

async def _refresh_participants_message(callback: CallbackQuery, bot: Bot, event_id: int):
    """Обновляет список в личке админа и сообщение в группе."""
    from handlers.user import format_event_message
    from keyboards import get_event_keyboard, get_admin_list_keyboard
    from db import get_event, get_participants, get_event_message_id

    event = get_event(event_id)
    participants = get_participants(event_id)

    # Обновляем сообщение в группе
    message_id = get_event_message_id(event_id)
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=format_event_message(event, participants),
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Не удалось обновить сообщение в группе: {e}")

    # Обновляем список участников в личке админа
    try:
        await callback.message.edit_text(
            text=(
                f"📋 <b>Список участников события:</b>\n"
                f"📅 {event[1]}\n\n"
                f"🟢 основной · 🟡 запасной\n\n"
                f"Нажмите на имя участника, чтобы открыть диалог (если есть @username)."
            ),
            parse_mode="HTML",
            reply_markup=get_admin_list_keyboard(event_id, participants)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить список: {e}")
