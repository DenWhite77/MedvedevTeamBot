"""
Модуль handlers/admin/events.py

Содержит обработчики для работы с событиями:
- Создание события (/new_event) с выбором адреса, времени начала и длительности
- Публикация события в топики
- Удаление событий
- Отмена диалога
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot

from config import GROUP_ID, TOPICS

from db import (
    create_event, get_event, get_event_message_id, get_all_events,
    mark_event_published, is_event_published, delete_event as db_delete_event,
    get_addresses, add_address,
    get_start_times, add_start_time,
    get_durations, add_duration,
    calculate_end_time,
)

from keyboards import (
    get_cancel_keyboard, get_skip_keyboard, get_main_menu,
    get_publish_keyboard, get_event_keyboard, get_topics_keyboard,
    get_addresses_keyboard,
    get_start_times_keyboard, get_durations_keyboard,
)

from .common import is_admin, build_event_summary

logger = logging.getLogger(__name__)

router = Router(name="admin_events")


class NewEventStates(StatesGroup):
    """Состояния пошагового диалога создания события."""
    direction = State()
    place = State()
    place_manual = State()
    date = State()
    time_start = State()            # выбор времени начала
    time_start_manual = State()     # ручной ввод времени начала
    time_duration = State()         # выбор длительности
    max_participants = State()
    price = State()
    payment_info = State()
    comment = State()


# ============================================================
# СОЗДАНИЕ СОБЫТИЯ
# ============================================================

@router.message(Command("new_event"))
async def new_event_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав на это действие.")
        return
    await state.clear()
    await message.answer(
        "📅 Создание нового события.\n\n"
        "Введите направление (например, «Волейбол классический»):\n"
        "Или нажмите «Отмена» для выхода.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.direction)


@router.callback_query(F.data == "new_event")
async def new_event_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав на это действие.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer(
        "📅 Создание нового события.\n\n"
        "Введите направление (например, «Волейбол классический»):\n"
        "Или нажмите «Отмена» для выхода.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.direction)
    await callback.answer()


@router.message(NewEventStates.direction)
async def process_direction(message: Message, state: FSMContext):
    await state.update_data(direction=message.text)

    addresses = get_addresses()
    if addresses:
        await message.answer(
            "📍 *Выберите место проведения:*\n\n"
            "⭐ — основной адрес.",
            parse_mode="Markdown",
            reply_markup=get_addresses_keyboard(addresses)
        )
        await state.set_state(NewEventStates.place)
    else:
        await message.answer(
            "📍 Введите адрес вручную:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.place_manual)


@router.callback_query(F.data.startswith("addr_pick_"))
async def address_picked(callback: CallbackQuery, state: FSMContext):
    addr_id = int(callback.data.split("_")[2])
    addresses = get_addresses()
    chosen = next((a for a in addresses if a[0] == addr_id), None)

    if not chosen:
        await callback.answer("⚠️ Адрес не найден.", show_alert=True)
        return

    await state.update_data(place=chosen[1])
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"📍 Место: *{chosen[1]}*", parse_mode="Markdown")
    await callback.message.answer(
        "📅 Введите дату (например, «17 сентября 2026»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.date)
    await callback.answer()


@router.callback_query(F.data == "addr_manual")
async def address_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📍 Введите адрес:\n\n"
        "Пример: ул. Подольских Курсантов, 16-А (Школа № 657)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.place_manual)
    await callback.answer()


@router.message(NewEventStates.place_manual)
async def process_place_manual(message: Message, state: FSMContext):
    address = message.text.strip()
    await state.update_data(place=address, pending_address=address)

    await message.answer(
        f"📍 Адрес: *{address}*\n\n"
        f"Сохранить его в библиотеку адресов?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="addr_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="addr_save_no")],
        ])
    )


@router.callback_query(F.data == "addr_save_yes")
async def address_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    address = data.get("pending_address")

    if address:
        result = add_address(address)
        if result:
            await callback.message.answer("✅ Адрес сохранён в библиотеку.")
        else:
            await callback.message.answer("ℹ️ Такой адрес уже есть в библиотеке.")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "📅 Введите дату (например, «17 сентября 2026»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.date)
    await callback.answer()


@router.callback_query(F.data == "addr_save_no")
async def address_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "📅 Введите дату (например, «17 сентября 2026»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.date)
    await callback.answer()


@router.message(NewEventStates.date)
async def process_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)

    start_times = get_start_times()
    if start_times:
        await message.answer(
            "🕐 *Выберите время начала:*",
            parse_mode="Markdown",
            reply_markup=get_start_times_keyboard(start_times)
        )
        await state.set_state(NewEventStates.time_start)
    else:
        await message.answer(
            "🕐 Введите время начала вручную (например, «20:00»):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.time_start_manual)


@router.callback_query(F.data.startswith("time_start_pick_"))
async def time_start_picked(callback: CallbackQuery, state: FSMContext):
    """Админ выбрал время начала из библиотеки."""
    time_id = int(callback.data.split("_")[3])
    start_times = get_start_times()
    chosen = next((t for t in start_times if t[0] == time_id), None)

    if not chosen:
        await callback.answer("⚠️ Время не найдено.", show_alert=True)
        return

    await state.update_data(time_start=chosen[1])

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        f"🕐 Время начала: *{chosen[1]}*",
        parse_mode="Markdown"
    )
    await _ask_for_duration(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "time_start_manual")
async def time_start_manual_start(callback: CallbackQuery, state: FSMContext):
    """Ручной ввод времени начала."""
    await callback.message.answer(
        "🕐 Введите время начала:\n\nПример: 20:00",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.time_start_manual)
    await callback.answer()


@router.message(NewEventStates.time_start_manual)
async def process_time_start_manual(message: Message, state: FSMContext):
    """Ручной ввод времени начала. Спрашиваем, сохранить ли в библиотеку."""
    time_str = message.text.strip()

    # Базовая валидация формата
    parts = time_str.replace(".", ":").split(":")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        await message.answer(
            "⚠️ Неверный формат. Введите время как `20:00`.",
            parse_mode="Markdown"
        )
        return

    await state.update_data(time_start=time_str, pending_start_time=time_str)

    await message.answer(
        f"🕐 Время начала: *{time_str}*\n\n"
        f"Сохранить в библиотеку времён?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="time_start_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="time_start_save_no")],
        ])
    )


@router.callback_query(F.data == "time_start_save_yes")
async def time_start_save_yes(callback: CallbackQuery, state: FSMContext):
    """Сохраняем время начала в библиотеку."""
    data = await state.get_data()
    time_str = data.get("pending_start_time")

    if time_str:
        result = add_start_time(time_str)
        if result:
            await callback.message.answer(f"✅ Время *{time_str}* сохранено.", parse_mode="Markdown")
        else:
            await callback.message.answer("ℹ️ Такое время уже есть.")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_duration(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "time_start_save_no")
async def time_start_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_duration(callback.message, state)
    await callback.answer()


async def _ask_for_duration(target_message, state: FSMContext):
    """Показывает клавиатуру выбора длительности."""
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
            "⏱ Введите длительность в часах (число, например «2»):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.time_duration)


@router.callback_query(F.data.startswith("duration_pick_"))
async def duration_picked(callback: CallbackQuery, state: FSMContext):
    """Админ выбрал длительность."""
    dur_id = int(callback.data.split("_")[2])
    durations = get_durations()
    chosen = next((d for d in durations if d[0] == dur_id), None)

    if not chosen:
        await callback.answer("⚠️ Длительность не найдена.", show_alert=True)
        return

    dur_id, hours, label = chosen
    data = await state.get_data()
    start_time = data.get("time_start", "??:??")
    end_time = calculate_end_time(start_time, hours)
    time_full = f"{start_time}–{end_time}"

    await state.update_data(time=time_full)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        f"✅ Итоговое время: *{time_full}*",
        parse_mode="Markdown"
    )
    await callback.message.answer(
        "👥 Введите максимальное количество участников (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.max_participants)
    await callback.answer()


@router.message(NewEventStates.time_duration)
async def process_duration_manual(message: Message, state: FSMContext):
    """Если библиотека длительностей пуста — ручной ввод числа часов."""
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Введите целое число часов (например, «2»).")
        return
    hours = int(message.text.strip())
    data = await state.get_data()
    start_time = data.get("time_start", "??:??")
    end_time = calculate_end_time(start_time, hours)
    time_full = f"{start_time}–{end_time}"

    await state.update_data(time=time_full)
    await message.answer(f"✅ Итоговое время: *{time_full}*", parse_mode="Markdown")
    await message.answer(
        "👥 Введите максимальное количество участников (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.max_participants)


@router.message(NewEventStates.max_participants)
async def process_max_participants(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите число.")
        return
    await state.update_data(max_participants=int(message.text))
    await message.answer(
        "💰 Введите стоимость (число, например, «650»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.price)


@router.message(NewEventStates.price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите число.")
        return
    await state.update_data(price=int(message.text))
    await message.answer(
        "💳 Введите способ оплаты (например, «Перевод на карту»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.payment_info)


@router.message(NewEventStates.payment_info)
async def process_payment_info(message: Message, state: FSMContext):
    await state.update_data(payment_info=message.text)
    await message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)


async def _finalize_event(message_or_callback, state: FSMContext, is_callback: bool):
    """Общая логика финализации создания события."""
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
        f"✅ Событие создано! ID: `{event_id}`.\n"
        f"Теперь его можно опубликовать в группе.",
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(NewEventStates.comment)
async def process_comment(message: Message, state: FSMContext):
    if message.text == "⏭ Пропустить":
        await state.update_data(comment="")
    else:
        await state.update_data(comment=message.text)
    await _finalize_event(message, state, is_callback=False)


@router.callback_query(F.data == "skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == NewEventStates.comment:
        await state.update_data(comment="")
        await _finalize_event(callback, state, is_callback=True)
        await callback.answer()
    else:
        await callback.answer("⚠️ Кнопка доступна только на шаге комментария.", show_alert=True)


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Действие отменено.", reply_markup=get_main_menu())
    await callback.answer()


# ============================================================
# ПУБЛИКАЦИЯ В ТОПИКИ
# ============================================================

@router.callback_query(F.data.startswith("publish_event_"))
async def publish_event(callback: CallbackQuery, bot: Bot):
    event_id = int(callback.data.split("_")[2])
    await callback.message.answer(
        "📤 Куда опубликовать событие?\n\nВыберите топик:",
        reply_markup=get_topics_keyboard(event_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topic_"))
async def publish_to_topic(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    topic_key = parts[1]
    event_id = int(parts[2])

    topic = TOPICS.get(topic_key)
    if not topic:
        await callback.answer("⚠️ Топик не найден.", show_alert=True)
        return

    if is_event_published(event_id):
        await callback.answer("⚠️ Это событие уже опубликовано!", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    text = (
        f"📅 *{event[1]}*\n\n"
        f"📍 *Место:* {event[3]}\n"
        f"📅 *Дата:* {event[4]}\n"
        f"🕐 *Время:* {event[5]}\n"
        f"👥 *Макс. участников:* {event[6]}\n"
        f"💰 *Стоимость:* {event[7]} ₽\n"
        f"💳 *Оплата:* {event[8]}\n"
        f"📝 *Комментарий:* {event[9] or '—'}\n\n"
        f"Нажмите «✅ Я в деле», чтобы записаться!"
    )

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

        logger.info(
            f"=== ПУБЛИКАЦИЯ ===\n"
            f"event_id={event_id}\n"
            f"topic={topic}\n"
            f"GROUP_ID={GROUP_ID}\n"
            f"sent.message_id={sent.message_id}\n"
            f"sent.chat.id={sent.chat.id}\n"
            f"sent.message_thread_id={getattr(sent, 'message_thread_id', None)}"
        )

        mark_event_published(event_id, topic["thread_id"], sent.message_id)
        await callback.message.answer(f"✅ Событие опубликовано в топик {topic['name']}!")

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось убрать кнопку: {e}")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при публикации: {e}")
    await callback.answer()


@router.message(Command("topic_id"))
async def get_topic_id(message: Message):
    thread_id = message.message_thread_id
    chat_id = message.chat.id
    await message.answer(
        f"📌 message_thread_id: {thread_id}\nchat_id: {chat_id}"
    )


# ============================================================
# УДАЛЕНИЕ СОБЫТИЙ
# ============================================================

@router.callback_query(F.data == "delete_event_list")
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
        event_id = event[0]
        title = event[1]
        date = event[4]
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {title} — {date}",
                callback_data=f"delete_{event_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Закрыть", callback_data="close_list")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        "🗑 *Выберите событие для удаления:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_") & ~F.data.startswith("delete_event_list"))
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
            logger.info(f"Сообщение {message_id} удалено из группы.")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение из группы: {e}")

    ok = db_delete_event(event_id)

    if ok:
        await callback.message.answer(f"🗑 Событие ID={event_id} удалено.")
    else:
        await callback.message.answer(
            f"⚠️ Событие ID={event_id} не найдено в БД (возможно, уже удалено)."
        )
    await callback.answer()


@router.callback_query(F.data == "close_list")
async def close_list(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    await callback.answer()


@router.callback_query(F.data == "edit_event_list")
async def edit_event_list(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return
    await callback.message.answer("✏️ Редактирование событий — функция в разработке.")
    await callback.answer()
