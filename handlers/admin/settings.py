"""
Модуль handlers/admin/settings.py

Управление библиотеками:
- Направления
- Адреса
- Времена начала
- Длительности
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from db import (
    get_directions, add_direction, delete_direction, set_default_direction,
    get_addresses, add_address, delete_address, set_default_address,
    get_start_times, add_start_time, delete_start_time,
    get_durations, add_duration, delete_duration,
)

from keyboards import (
    get_cancel_keyboard, get_main_menu, get_settings_menu,
    get_directions_management_keyboard, get_direction_info_keyboard,
    get_address_management_keyboard, get_address_info_keyboard,
    get_start_times_management_keyboard, get_durations_management_keyboard,
)

from .common import is_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_settings")


class DirectionStates(StatesGroup):
    add = State()


class AddressStates(StatesGroup):
    add = State()


class StartTimeStates(StatesGroup):
    add = State()


class DurationStates(StatesGroup):
    add_hours = State()
    add_label = State()


# ============================================================
# ГЛАВНОЕ МЕНЮ НАСТРОЕК
# ============================================================

@router.callback_query(F.data == "settings_menu")
async def settings_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ *Настройки*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=get_settings_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============================================================
# УПРАВЛЕНИЕ НАПРАВЛЕНИЯМИ
# ============================================================

@router.callback_query(F.data == "manage_directions")
async def manage_directions(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    directions = get_directions()
    text = "🏐 *Управление направлениями*\n\n"
    if not directions:
        text += "_Список пуст._"
    else:
        text += "⭐ — основное направление.\nНажмите на направление для действий."

    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_directions_management_keyboard(directions)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_directions_management_keyboard(directions)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("direction_info_"))
async def direction_info(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    dir_id = int(callback.data.split("_")[2])
    directions = get_directions()
    chosen = next((d for d in directions if d[0] == dir_id), None)
    if not chosen:
        await callback.answer("⚠️ Направление не найдено.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🏐 *Направление:*\n{chosen[1]}\n\n"
        f"⭐ Основное: {'да' if chosen[2] else 'нет'}",
        parse_mode="Markdown",
        reply_markup=get_direction_info_keyboard(dir_id, bool(chosen[2]))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("direction_set_default_"))
async def direction_set_default(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    dir_id = int(callback.data.split("_")[3])
    set_default_direction(dir_id)
    await callback.answer("⭐ Направление сделано основным.")
    await manage_directions(callback)


@router.callback_query(F.data.startswith("direction_del_"))
async def direction_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    dir_id = int(callback.data.split("_")[2])
    ok = delete_direction(dir_id)
    if ok:
        await callback.answer("🗑 Направление удалено.")
    else:
        await callback.answer("⚠️ Направление не найдено.", show_alert=True)
    await manage_directions(callback)


@router.callback_query(F.data == "direction_add")
async def direction_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "🏐 Введите направление:\n\nПример: Волейбол классический",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(DirectionStates.add)
    await callback.answer()


@router.message(DirectionStates.add)
async def direction_add_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    name = message.text.strip()
    result = add_direction(name)
    if result:
        await message.answer(f"✅ Направление *{name}* добавлено.", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ Такое направление уже есть.")
    await state.clear()


# ============================================================
# УПРАВЛЕНИЕ АДРЕСАМИ
# ============================================================

@router.callback_query(F.data == "manage_addresses")
async def manage_addresses(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    addresses = get_addresses()
    text = "📍 *Управление адресами*\n\n"
    if not addresses:
        text += "_Список пуст._"
    else:
        text += "⭐ — основной адрес.\nНажмите на адрес для действий."

    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_address_management_keyboard(addresses)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_address_management_keyboard(addresses)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("addr_info_"))
async def addr_info(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    addr_id = int(callback.data.split("_")[2])
    addresses = get_addresses()
    chosen = next((a for a in addresses if a[0] == addr_id), None)
    if not chosen:
        await callback.answer("⚠️ Адрес не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📍 *Адрес:*\n{chosen[1]}\n\n"
        f"⭐ Основной: {'да' if chosen[2] else 'нет'}",
        parse_mode="Markdown",
        reply_markup=get_address_info_keyboard(addr_id, bool(chosen[2]))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addr_set_default_"))
async def addr_set_default(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    addr_id = int(callback.data.split("_")[3])
    set_default_address(addr_id)
    await callback.answer("⭐ Адрес сделан основным.")
    await manage_addresses(callback)


@router.callback_query(F.data.startswith("addr_del_"))
async def addr_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    addr_id = int(callback.data.split("_")[2])
    ok = delete_address(addr_id)
    if ok:
        await callback.answer("🗑 Адрес удалён.")
    else:
        await callback.answer("⚠️ Адрес не найден.", show_alert=True)
    await manage_addresses(callback)


@router.callback_query(F.data == "addr_add")
async def addr_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "📍 Введите адрес:\n\nПример: ул. Подольских Курсантов, 16-А (Школа № 657)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AddressStates.add)
    await callback.answer()


@router.message(AddressStates.add)
async def addr_add_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    address = message.text.strip()
    result = add_address(address)
    if result:
        await message.answer("✅ Адрес добавлен в библиотеку.")
    else:
        await message.answer("ℹ️ Такой адрес уже есть.")
    await state.clear()


# ============================================================
# УПРАВЛЕНИЕ ВРЕМЕНАМИ НАЧАЛА
# ============================================================

@router.callback_query(F.data == "manage_start_times")
async def manage_start_times(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    start_times = get_start_times()
    text = "🕐 *Управление временами начала*\n\n"
    if not start_times:
        text += "_Список пуст._"
    else:
        text += "Нажмите 🗑 для удаления."

    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_start_times_management_keyboard(start_times)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_start_times_management_keyboard(start_times)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("start_time_del_"))
async def start_time_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    time_id = int(callback.data.split("_")[3])
    ok = delete_start_time(time_id)
    if ok:
        await callback.answer("🗑 Время удалено.")
    else:
        await callback.answer("⚠️ Время не найдено.", show_alert=True)
    await manage_start_times(callback)


@router.callback_query(F.data.startswith("start_time_info_"))
async def start_time_info(callback: CallbackQuery):
    await callback.answer("Нажмите 🗑, чтобы удалить это время.", show_alert=False)


@router.callback_query(F.data == "start_time_add")
async def start_time_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "🕐 Введите время начала:\n\nПример: 20:00",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(StartTimeStates.add)
    await callback.answer()


@router.message(StartTimeStates.add)
async def start_time_add_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    time_str = message.text.strip()
    parts = time_str.replace(".", ":").split(":")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        await message.answer("⚠️ Неверный формат. Введите как `20:00`.", parse_mode="Markdown")
        return

    result = add_start_time(time_str)
    if result:
        await message.answer(f"✅ Время *{time_str}* добавлено.", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ Такое время уже есть.")
    await state.clear()


# ============================================================
# УПРАВЛЕНИЕ ДЛИТЕЛЬНОСТЯМИ
# ============================================================

@router.callback_query(F.data == "manage_durations")
async def manage_durations(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    durations = get_durations()
    text = "⏱ *Управление длительностями*\n\n"
    if not durations:
        text += "_Список пуст._"
    else:
        text += "Нажмите 🗑 для удаления."

    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_durations_management_keyboard(durations)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_durations_management_keyboard(durations)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("duration_del_"))
async def duration_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    dur_id = int(callback.data.split("_")[2])
    ok = delete_duration(dur_id)
    if ok:
        await callback.answer("🗑 Длительность удалена.")
    else:
        await callback.answer("⚠️ Длительность не найдена.", show_alert=True)
    await manage_durations(callback)


@router.callback_query(F.data.startswith("duration_info_"))
async def duration_info(callback: CallbackQuery):
    await callback.answer("Нажмите 🗑, чтобы удалить.", show_alert=False)


@router.callback_query(F.data == "duration_add")
async def duration_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "⏱ Введите длительность в часах (целое число, например «2»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(DurationStates.add_hours)
    await callback.answer()


@router.message(DurationStates.add_hours)
async def duration_add_hours(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    text = message.text.strip()
    if not text.isdigit() or int(text) < 1 or int(text) > 24:
        await message.answer("⚠️ Введите целое число часов от 1 до 24.")
        return

    await state.update_data(hours=int(text))
    await message.answer(
        "📝 Введите текстовую метку (например, «2 часа», «Полтора часа»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(DurationStates.add_label)


@router.message(DurationStates.add_label)
async def duration_add_label(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    label = message.text.strip()
    data = await state.get_data()
    hours = data.get("hours")

    result = add_duration(hours, label)
    if result:
        await message.answer(f"✅ Длительность *{label}* ({hours}ч) добавлена.", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ Такая длительность уже есть.")
    await state.clear()
