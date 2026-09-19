"""
Модуль handlers/admin/settings.py

Содержит обработчики для управления библиотеками:
- Адреса (просмотр, добавление, удаление, установка основного)
- Шаблоны времени (просмотр, добавление, удаление)
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from db import (
    get_addresses, add_address, delete_address, set_default_address,
    get_time_slots, add_time_slot, delete_time_slot,
)

from keyboards import (
    get_cancel_keyboard, get_main_menu, get_settings_menu,
    get_address_management_keyboard, get_address_info_keyboard,
    get_time_slots_management_keyboard,
)

from .common import is_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_settings")


class AddressStates(StatesGroup):
    """Состояния для управления адресами."""
    add = State()


class TimeSlotStates(StatesGroup):
    """Состояния для управления слотами времени."""
    add_start = State()
    add_end = State()


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
        # Если сообщение не редактируется (например, после другого действия)
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
        "📍 Введите адрес:\n\n"
        "Пример: ул. Подольских Курсантов, 16-А (Школа № 657)",
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
# УПРАВЛЕНИЕ ШАБЛОНАМИ ВРЕМЕНИ
# ============================================================

@router.callback_query(F.data == "manage_time_slots")
async def manage_time_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    slots = get_time_slots()
    text = "🕐 *Управление шаблонами времени*\n\n"
    if not slots:
        text += "_Список пуст._"
    else:
        text += "Нажмите 🗑 для удаления."

    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_time_slots_management_keyboard(slots)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_time_slots_management_keyboard(slots)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("slot_del_"))
async def slot_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    slot_id = int(callback.data.split("_")[2])
    ok = delete_time_slot(slot_id)
    if ok:
        await callback.answer("🗑 Шаблон удалён.")
    else:
        await callback.answer("⚠️ Шаблон не найден.", show_alert=True)
    await manage_time_slots(callback)


@router.callback_query(F.data == "slot_add")
async def slot_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "🕐 Введите время начала (например, «20:00»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TimeSlotStates.add_start)
    await callback.answer()


@router.message(TimeSlotStates.add_start)
async def slot_add_start_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    await state.update_data(start_time=message.text.strip())
    await message.answer(
        "🕐 Введите время окончания (например, «22:00»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TimeSlotStates.add_end)


@router.message(TimeSlotStates.add_end)
async def slot_add_end_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав.")
        return

    end_time = message.text.strip()
    data = await state.get_data()
    start_time = data["start_time"]

    try:
        sh, sm = map(int, start_time.split(":"))
        eh, em = map(int, end_time.split(":"))
        duration_min = (eh * 60 + em) - (sh * 60 + sm)
        duration_h = duration_min // 60
        duration_label = f"{duration_h}ч" if duration_min % 60 == 0 else f"{duration_min}мин"
    except Exception:
        duration_label = "?"

    label = f"{start_time}–{end_time} ({duration_label})"

    result = add_time_slot(start_time, end_time, label)
    if result:
        await message.answer(f"✅ Шаблон *{label}* добавлен.", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ Такой шаблон уже есть.")
    await state.clear()
