"""
Модуль keyboards.py

Содержит клавиатуры и кнопки для бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TOPICS


# ============================================================
# Общие клавиатуры
# ============================================================

def get_main_menu():
    """Главное меню (для админа)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Создать событие", callback_data="new_event")],
        [InlineKeyboardButton(text="✏️ Редактировать событие", callback_data="edit_event_list")],
        [InlineKeyboardButton(text="🗑 Удалить событие", callback_data="delete_event_list")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
    ])
    return keyboard


def get_cancel_keyboard():
    """Кнопка отмены для пошагового диалога."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_skip_keyboard():
    """Кнопка пропуска шага."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


# ============================================================
# Клавиатуры для админа — события
# ============================================================

def get_publish_keyboard(event_id):
    """Кнопка публикации события (с ID события)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Опубликовать в группу",
            callback_data=f"publish_event_{event_id}"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_admin_event_keyboard(event_id):
    """Кнопки для админа под событием."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список участников", callback_data=f"list_{event_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{event_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{event_id}")],
    ])
    return keyboard


def get_admin_list_keyboard(event_id, participants):
    """Клавиатура со списком участников и кнопками выписки (для админа)."""
    buttons = []
    for p in participants:
        user_id, username, full_name, status, paid = p
        name = full_name or username or f"id{user_id}"
        marker = "✅" if status == "main" else "🕐"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ Выписать {marker} {name}",
                callback_data=f"remove_{event_id}_{user_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Закрыть", callback_data="close_list")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# Клавиатуры для участников
# ============================================================

def get_event_keyboard(event_id):
    """Кнопки для участников под событием (без кнопки Список участников)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я в деле", callback_data=f"join_{event_id}")],
        [InlineKeyboardButton(text="💳 Оплатил", callback_data=f"paid_{event_id}")],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{event_id}")],
    ])
    return keyboard


def get_topics_keyboard(event_id):
    """Клавиатура с выбором топика для публикации (с ID события)."""
    buttons = []
    for key, topic in TOPICS.items():
        buttons.append([
            InlineKeyboardButton(
                text=topic["name"],
                callback_data=f"topic_{key}_{event_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_confirm_keyboard(event_id, user_id):
    """Кнопки подтверждения оплаты для админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"confirm_payment_{event_id}_{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_payment_{event_id}_{user_id}"
            ),
        ],
    ])
    return keyboard


# ============================================================
# НОВОЕ: Выбор адреса при создании события
# ============================================================

def get_addresses_keyboard(addresses, default_address=None):
    """
    Клавиатура выбора адреса.
    addresses: список кортежей (id, address, is_default) из db.get_addresses()
    """
    buttons = []
    for addr_id, address, is_default in addresses:
        # Обрезаем длинный адрес для кнопки
        label = address if len(address) <= 40 else address[:37] + "..."
        prefix = "⭐ " if is_default else "📍 "
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"addr_pick_{addr_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✏️ Ввести адрес вручную", callback_data="addr_manual")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# НОВОЕ: Выбор времени при создании события
# ============================================================

def get_start_times_keyboard(start_times):
    """
    Клавиатура выбора времени начала.
    start_times: список кортежей (id, time) из db.get_start_times()
    """
    buttons = []
    # По 2 кнопки в ряд
    row = []
    for time_id, time_str in start_times:
        row.append(InlineKeyboardButton(
            text=f"🕐 {time_str}",
            callback_data=f"time_start_pick_{time_id}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="time_start_manual")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_durations_keyboard(durations):
    """
    Клавиатура выбора длительности.
    durations: список кортежей (id, hours, label) из db.get_durations()
    """
    buttons = []
    row = []
    for dur_id, hours, label in durations:
        row.append(InlineKeyboardButton(
            text=f"⏱ {label}",
            callback_data=f"duration_pick_{dur_id}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# НОВОЕ: Админ-меню управления библиотеками
# ============================================================

def get_settings_menu():
    """Меню настроек (⚙️ Настройки)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Адреса", callback_data="manage_addresses")],
        [InlineKeyboardButton(text="🕐 Время начала", callback_data="manage_start_times")],
        [InlineKeyboardButton(text="⏱ Длительность", callback_data="manage_durations")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ])
    return keyboard


def get_address_management_keyboard(addresses):
    """
    Клавиатура управления адресами (для админа).
    addresses: список кортежей (id, address, is_default)
    """
    buttons = []
    for addr_id, address, is_default in addresses:
        label = address if len(address) <= 35 else address[:32] + "..."
        prefix = "⭐" if is_default else "📍"
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix} {label}",
                callback_data=f"addr_info_{addr_id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"addr_del_{addr_id}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить адрес", callback_data="addr_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_address_info_keyboard(address_id, is_default):
    """
    Клавиатура для конкретного адреса — что с ним делать.
    """
    buttons = []
    if not is_default:
        buttons.append([
            InlineKeyboardButton(
                text="⭐ Сделать основным",
                callback_data=f"addr_set_default_{address_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить адрес",
            callback_data=f"addr_del_{address_id}"
        )
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 К списку адресов", callback_data="manage_addresses")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_start_times_management_keyboard(start_times):
    """
    Клавиатура управления временами начала (для админа).
    start_times: список кортежей (id, time)
    """
    buttons = []
    row = []
    for time_id, time_str in start_times:
        row.append(InlineKeyboardButton(
            text=f"🕐 {time_str}",
            callback_data=f"start_time_info_{time_id}"
        ))
        row.append(InlineKeyboardButton(
            text="🗑",
            callback_data=f"start_time_del_{time_id}"
        ))
        buttons.append(row)
        row = []

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить время", callback_data="start_time_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_durations_management_keyboard(durations):
    """
    Клавиатура управления длительностями (для админа).
    durations: список кортежей (id, hours, label)
    """
    buttons = []
    for dur_id, hours, label in durations:
        buttons.append([
            InlineKeyboardButton(
                text=f"⏱ {label}",
                callback_data=f"duration_info_{dur_id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"duration_del_{dur_id}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить длительность", callback_data="duration_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
