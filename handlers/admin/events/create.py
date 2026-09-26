"""
Модуль handlers/admin/events/create.py

Пошаговое создание события:
- направление, адрес, дата (календарь), время начала, длительность,
- макс. участников, цена, способ оплаты, комментарий.
Плюс: skip, cancel.
"""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from db import (
    add_direction,
    add_address,
    add_start_time,
    add_payment_method,
    calculate_end_time,
    get_payment_method,
    get_payment_methods,
    get_start_times,
    get_durations,
    format_payment_info,
)

from keyboards import (
    get_cancel_keyboard,
    get_skip_keyboard,
    get_main_menu,
    get_start_times_keyboard,
    get_durations_keyboard,
    get_payment_methods_keyboard,
)

from .states import NewEventStates, format_date_ru
from .helpers import (
    _ask_for_direction,
    _ask_for_place,
    _ask_for_date,
    _ask_for_duration,
    _finalize_event,
)
from ..common import is_admin

logger = logging.getLogger(__name__)

router_create = Router(name="admin_events_create")


# ============================================================
# СТАРТ СОЗДАНИЯ
# ============================================================

@router_create.message(Command("new_event"))
async def new_event_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав на это действие.")
        return
    await state.clear()
    await _ask_for_direction(message, state)


@router_create.callback_query(F.data == "new_event")
async def new_event_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return
    await state.clear()
    await _ask_for_direction(callback.message, state)
    await callback.answer()


# ============================================================
# НАПРАВЛЕНИЕ
# ============================================================

@router_create.callback_query(F.data.startswith("direction_pick_"))
async def direction_picked(callback: CallbackQuery, state: FSMContext):
    dir_id = int(callback.data.split("_")[2])
    from db import get_directions
    directions = get_directions()
    chosen = next((d for d in directions if d[0] == dir_id), None)

    if not chosen:
        await callback.answer("⚠️ Направление не найдено.", show_alert=True)
        return

    await state.update_data(direction=chosen[1])
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"🏐 Направление: *{chosen[1]}*", parse_mode="Markdown")
    await _ask_for_place(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "direction_manual")
async def direction_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🏐 Введите направление:\n\nПример: Волейбол классический",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.direction_manual)
    await callback.answer()


@router_create.message(NewEventStates.direction_manual)
async def process_direction_manual(message: Message, state: FSMContext):
    direction = message.text.strip()
    await state.update_data(direction=direction, pending_direction=direction)

    await message.answer(
        f"🏐 Направление: *{direction}*\n\nСохранить в библиотеку?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="direction_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="direction_save_no")],
        ])
    )


@router_create.callback_query(F.data == "direction_save_yes")
async def direction_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    direction = data.get("pending_direction")
    if direction:
        if add_direction(direction):
            await callback.message.answer("✅ Направление сохранено.")
        else:
            await callback.message.answer("ℹ️ Такое направление уже есть.")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_place(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "direction_save_no")
async def direction_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_place(callback.message, state)
    await callback.answer()


# ============================================================
# АДРЕС
# ============================================================

@router_create.callback_query(F.data.startswith("addr_pick_"))
async def address_picked(callback: CallbackQuery, state: FSMContext):
    addr_id = int(callback.data.split("_")[2])
    from db import get_addresses
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
    await _ask_for_date(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "addr_manual")
async def address_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📍 Введите адрес:\n\nПример: ул. Подольских Курсантов, 16-А (Школа № 657)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.place_manual)
    await callback.answer()


@router_create.message(NewEventStates.place_manual)
async def process_place_manual(message: Message, state: FSMContext):
    address = message.text.strip()
    await state.update_data(place=address, pending_address=address)

    await message.answer(
        f"📍 Адрес: *{address}*\n\nСохранить в библиотеку адресов?\n"
        f"_(координаты подтянутся автоматически)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="addr_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="addr_save_no")],
        ])
    )


@router_create.callback_query(F.data == "addr_save_yes")
async def address_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    address = data.get("pending_address")

    if address:
        addr_id = await add_address(address)
        if addr_id:
            await callback.message.answer("✅ Адрес сохранён (координаты определены).")
        else:
            await callback.message.answer("ℹ️ Такой адрес уже есть в библиотеке.")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_date(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "addr_save_no")
async def address_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_date(callback.message, state)
    await callback.answer()


# ============================================================
# ДАТА
# ============================================================

@router_create.callback_query(SimpleCalendarCallback.filter())
async def process_calendar_date(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    try:
        calendar = SimpleCalendar(locale='ru_RU')
        selected, date = await calendar.process_selection(callback, callback_data)
    except Exception:
        calendar = SimpleCalendar()
        selected, date = await calendar.process_selection(callback, callback_data)

    if not selected:
        await callback.answer()
        return

    formatted = format_date_ru(date)
    await state.update_data(date=formatted)

    try:
        await callback.message.edit_text(
            f"📅 Дата: *{formatted}*",
            parse_mode="Markdown"
        )
    except Exception:
        await callback.message.answer(f"📅 Дата: *{formatted}*", parse_mode="Markdown")

    start_times = get_start_times()
    if start_times:
        await callback.message.answer(
            "🕐 *Выберите время начала:*",
            parse_mode="Markdown",
            reply_markup=get_start_times_keyboard(start_times)
        )
        await state.set_state(NewEventStates.time_start)
    else:
        await callback.message.answer(
            "🕐 Введите время начала вручную (например, «20:00»):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.time_start_manual)

    await callback.answer()


# ============================================================
# ВРЕМЯ НАЧАЛА
# ============================================================

@router_create.callback_query(F.data.startswith("time_start_pick_"))
async def time_start_picked(callback: CallbackQuery, state: FSMContext):
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
    await callback.message.answer(f"🕐 Время начала: *{chosen[1]}*", parse_mode="Markdown")
    await _ask_for_duration(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "time_start_manual")
async def time_start_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🕐 Введите время начала:\n\nПример: 20:00",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.time_start_manual)
    await callback.answer()


@router_create.message(NewEventStates.time_start_manual)
async def process_time_start_manual(message: Message, state: FSMContext):
    time_str = message.text.strip()
    parts = time_str.replace(".", ":").split(":")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        await message.answer("⚠️ Неверный формат. Введите как `20:00`.", parse_mode="Markdown")
        return

    await state.update_data(time_start=time_str, pending_start_time=time_str)
    await message.answer(
        f"🕐 Время начала: *{time_str}*\n\nСохранить в библиотеку?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="time_start_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="time_start_save_no")],
        ])
    )


@router_create.callback_query(F.data == "time_start_save_yes")
async def time_start_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    time_str = data.get("pending_start_time")
    if time_str:
        if add_start_time(time_str):
            await callback.message.answer(f"✅ Время *{time_str}* сохранено.", parse_mode="Markdown")
        else:
            await callback.message.answer("ℹ️ Такое время уже есть.")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_duration(callback.message, state)
    await callback.answer()


@router_create.callback_query(F.data == "time_start_save_no")
async def time_start_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _ask_for_duration(callback.message, state)
    await callback.answer()


# ============================================================
# ДЛИТЕЛЬНОСТЬ
# ============================================================

@router_create.callback_query(F.data.startswith("duration_pick_"))
async def duration_picked(callback: CallbackQuery, state: FSMContext):
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
    await callback.message.answer(f"✅ Итоговое время: *{time_full}*", parse_mode="Markdown")
    await callback.message.answer(
        "👥 Введите максимальное количество участников (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.max_participants)
    await callback.answer()


@router_create.message(NewEventStates.time_duration)
async def process_duration_manual(message: Message, state: FSMContext):
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


# ============================================================
# МАКС. УЧАСТНИКОВ / ЦЕНА / ОПЛАТА / КОММЕНТАРИЙ
# ============================================================

@router_create.message(NewEventStates.max_participants)
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


@router_create.message(NewEventStates.price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите число.")
        return
    await state.update_data(price=int(message.text))

    methods = get_payment_methods()
    if methods:
        await message.answer(
            "💳 *Выберите способ оплаты:*\n\n⭐ — основной.",
            parse_mode="Markdown",
            reply_markup=get_payment_methods_keyboard(methods)
        )
        await state.set_state(NewEventStates.payment_pick)
    else:
        await message.answer(
            "💳 Введите название способа оплаты (например, «Перевод на карту»):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(NewEventStates.payment_manual)


@router_create.callback_query(F.data.startswith("payment_pick_"))
async def payment_picked(callback: CallbackQuery, state: FSMContext):
    pm_id = int(callback.data.split("_")[2])
    method = get_payment_method(pm_id)

    if not method:
        await callback.answer("⚠️ Способ не найден.", show_alert=True)
        return

    pm_id, name, bank, details, is_default = method
    text_info = format_payment_info(name, bank, details)
    await state.update_data(payment_info=text_info)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"💳 Оплата: *{name}*" + (f" {bank}" if bank else "") +
        (f"\n`{details}`" if details else ""),
        parse_mode="Markdown"
    )
    await callback.message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)
    await callback.answer()


@router_create.callback_query(F.data == "payment_manual")
async def payment_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💳 Введите название способа оплаты:\n\nПример: Перевод на карту",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.payment_manual)
    await callback.answer()


@router_create.message(NewEventStates.payment_manual)
async def process_payment_manual(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(pending_payment_name=name)

    await message.answer(
        f"💳 Название: *{name}*\n\n"
        f"Введите банк и реквизиты одной строкой:\n\n"
        f"Или нажмите «⏭ Пропустить».",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="payment_details_skip")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ])
    )
    await state.set_state(NewEventStates.payment_manual_details)


@router_create.message(NewEventStates.payment_manual_details)
async def process_payment_manual_details(message: Message, state: FSMContext):
    details_line = message.text.strip()
    data = await state.get_data()
    name = data.get("pending_payment_name")

    bank = details_line
    details = None
    if " " in details_line:
        parts = details_line.rsplit(" ", 1)
        if parts[-1].startswith("+") or parts[-1].replace("-", "").replace(" ", "").isdigit():
            bank = parts[0]
            details = parts[1]

    text_info = format_payment_info(name, bank, details)
    await state.update_data(payment_info=text_info, pending_payment_full=(name, bank, details))

    await message.answer(
        f"💳 Оплата: *{text_info}*\n\nСохранить в библиотеку?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="payment_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="payment_save_no")],
        ])
    )


@router_create.callback_query(F.data == "payment_details_skip")
async def payment_details_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get("pending_payment_name")
    text_info = format_payment_info(name, None, None)
    await state.update_data(payment_info=text_info, pending_payment_full=(name, None, None))

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"💳 Оплата: *{text_info}*\n\nСохранить в библиотеку?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="payment_save_yes")],
            [InlineKeyboardButton(text="➡️ Не сохранять", callback_data="payment_save_no")],
        ])
    )
    await callback.answer()


@router_create.callback_query(F.data == "payment_save_yes")
async def payment_save_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    full = data.get("pending_payment_full")
    if full:
        name, bank, details = full
        if add_payment_method(name, bank, details):
            await callback.message.answer("✅ Способ оплаты сохранён.")
        else:
            await callback.message.answer("ℹ️ Такой способ уже есть.")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)
    await callback.answer()


@router_create.callback_query(F.data == "payment_save_no")
async def payment_save_no(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)
    await callback.answer()


# ============================================================
# КОММЕНТАРИЙ + SKIP + CANCEL
# ============================================================

@router_create.message(NewEventStates.comment)
async def process_comment(message: Message, state: FSMContext):
    if message.text == "⏭ Пропустить":
        await state.update_data(comment="")
    else:
        await state.update_data(comment=message.text)
    await _finalize_event(message, state, is_callback=False)


@router_create.callback_query(F.data == "skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == NewEventStates.comment:
        await state.update_data(comment="")
        await _finalize_event(callback, state, is_callback=True)
        await callback.answer()
    else:
        await callback.answer(
            "⚠️ Кнопка доступна только на шаге комментария.",
            show_alert=True
        )


@router_create.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


@router_create.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Действие отменено.", reply_markup=get_main_menu())
    await callback.answer()
    