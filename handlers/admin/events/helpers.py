"""
Модуль handlers/admin/events/helpers.py

Хелперы для создания события:
- _ask_for_direction, _ask_for_place, _ask_for_date, _ask_for_duration
- _finalize_event
"""
import logging

from aiogram.fsm.context import FSMContext

from db import (
    create_event,
    get_directions,
    get_addresses,
    get_start_times,
    get_durations,
)

from keyboards import (
    get_cancel_keyboard,
    get_publish_keyboard,
    get_directions_keyboard,
    get_addresses_keyboard,
    get_start_times_keyboard,
    get_durations_keyboard,
    get_calendar_keyboard,
)

from .states import NewEventStates
from ..common import build_event_summary

logger = logging.getLogger(__name__)


async def _ask_for_direction(target_message, state: FSMContext):
    directions = get_directions()
    if directions:
        await target_message.answer(
            "🏐 *Выберите направление:*\n\n⭐ — основное.",
            parse_mode="Markdown",
            reply_markup=get_directions_keyboard(directions)
        )
        await state.set_state(NewEventStates.direction)
    else:
        await target_message.answer(
            "🏐 Введите направление вручную:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.direction_manual)


async def _ask_for_place(target_message, state: FSMContext):
    addresses = get_addresses()
    if addresses:
        await target_message.answer(
            "📍 *Выберите место проведения:*\n\n⭐ — основной адрес.",
            parse_mode="Markdown",
            reply_markup=get_addresses_keyboard(addresses)
        )
        await state.set_state(NewEventStates.place)
    else:
        await target_message.answer(
            "📍 Введите адрес вручную:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.place_manual)


async def _ask_for_date(target_message, state: FSMContext):
    await target_message.answer(
        "📅 *Выберите дату:*",
        parse_mode="Markdown",
        reply_markup=await get_calendar_keyboard()
    )
    await state.set_state(NewEventStates.date)


async def _ask_for_duration(target_message, state: FSMContext):
    durations = get_durations()
    if durations:
        await target_message.answer(
            "⏱ *Выберите длительность:*",
            parse_mode="Markdown",
            reply_markup=get_durations_keyboard(durations)
        )
        await state.set_state(NewEventStates.time_duration)
    else:
        await target_message.answer(
            "⏱ Введите длительность в часах (например, «2»):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.time_duration)


async def _finalize_event(message_or_callback, state: FSMContext, is_callback: bool):
    """Финальная сборка события: создание в БД + сводка + кнопка публикации."""
    data = await state.get_data()
    summary = build_event_summary(data)

    event_id = create_event(
        title=data['direction'],
        direction=data['direction'],
        place=data['place'],
        date=data['date'],
        time=data['time'],
        max_participants=data['max_participants'],
        price=data['price'],
        payment_info=data['payment_info'],
        comment=data.get('comment', '')
    )

    target = message_or_callback.message if is_callback else message_or_callback
    await target.answer(
        summary,
        parse_mode="Markdown",
        reply_markup=get_publish_keyboard(event_id)
    )
    await target.answer(
        f"✅ Событие создано! ID: `{event_id}`.\nТеперь его можно опубликовать.",
        parse_mode="Markdown"
    )
    await state.clear()
    