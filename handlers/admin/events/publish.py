"""
Модуль handlers/admin/events/publish.py

Публикация события в топики группы.
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram import Bot

from config import GROUP_ID, TOPICS

from db import (
    get_event,
    is_event_published,
    mark_event_published,
)

from keyboards import (
    get_event_keyboard,
    get_topics_keyboard,
)

logger = logging.getLogger(__name__)

router_publish = Router(name="admin_events_publish")


@router_publish.callback_query(F.data.startswith("publish_event_"))
async def publish_event(callback: CallbackQuery, bot: Bot):
    event_id = int(callback.data.split("_")[2])
    await callback.message.answer(
        "📤 Куда опубликовать событие?\n\nВыберите топик:",
        reply_markup=get_topics_keyboard(event_id)
    )
    await callback.answer()


@router_publish.callback_query(F.data.startswith("topic_"))
async def publish_to_topic(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    topic_key = parts[1]
    event_id = int(parts[2])

    topic = TOPICS.get(topic_key)
    if not topic:
        await callback.answer("⚠️ Топик не найден.", show_alert=True)
        return

    if is_event_published(event_id):
        await callback.answer("⚠️ Событие уже опубликовано!", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    # Используем единую функцию сборки текста (со ссылкой на Яндекс.Карты)
    from handlers.user import format_event_message
    text = format_event_message(event, participants=[])

    try:
        if topic["thread_id"] is None:
            sent = await bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        else:
            sent = await bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic["thread_id"],
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )

        mark_event_published(event_id, topic["thread_id"], sent.message_id)
        await callback.message.answer(f"✅ Событие опубликовано в топик {topic['name']}!")

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при публикации: {e}")
    await callback.answer()


@router_publish.message(Command("topic_id"))
async def get_topic_id(message: Message):
    await message.answer(
        f"📌 message_thread_id: {message.message_thread_id}\nchat_id: {message.chat.id}"
    )
    