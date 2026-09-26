"""
Модуль handlers/admin/events/delete.py

Удаление событий + заглушка для редактирования.
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot

from config import GROUP_ID

from db import (
    get_all_events,
    get_event,
    get_event_message_id,
    delete_event as db_delete_event,
)

from ..common import is_admin

logger = logging.getLogger(__name__)

router_delete = Router(name="admin_events_delete")


@router_delete.callback_query(F.data == "delete_event_list")
async def delete_event_list(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    events = get_all_events()
    if not events:
        await callback.message.answer("⚠️ Нет активных событий.")
        await callback.answer()
        return

    buttons = []
    for event in events:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {event[1]} — {event[4]}",
                callback_data=f"delete_{event[0]}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="close_list")])

    await callback.message.answer(
        "🗑 *Выберите событие для удаления:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router_delete.callback_query(F.data.startswith("delete_") & ~F.data.startswith("delete_event_list"))
async def delete_event(callback: CallbackQuery, bot: Bot):
    event_id = int(callback.data.split("_")[1])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    message_id = get_event_message_id(event_id)
    if message_id:
        try:
            await bot.delete_message(chat_id=GROUP_ID, message_id=message_id)
            logger.info(f"Message {message_id} deleted from group.")
        except Exception as e:
            logger.warning(f"Cannot delete message from group: {e}")

    ok = db_delete_event(event_id)
    if ok:
        await callback.message.answer(f"🗑 Событие ID={event_id} удалено.")
    else:
        await callback.message.answer(f"⚠️ Событие ID={event_id} не найдено.")
    await callback.answer()


@router_delete.callback_query(F.data == "close_list")
async def close_list(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router_delete.callback_query(F.data == "edit_event_list")
async def edit_event_list(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return
    await callback.message.answer("✏️ Редактирование событий — в разработке.")
    await callback.answer()
