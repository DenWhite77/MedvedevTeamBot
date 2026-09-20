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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Создать событие", callback_data="new_event")],
        [InlineKeyboardButton(text="✏️ Редактировать событие", callback_data="edit_event_list")],
        [InlineKeyboardButton(text="🗑 Удалить событие", callback_data="delete_event_list")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
    ])
    return keyboard


def get_cancel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_skip_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


# ============================================================
# Клавиатуры для админа — события
# ============================================================

def get_publish_keyboard(event_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Опубликовать в группу",
            callback_data=f"publish_event_{event_id}"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_admin_event_keyboard(event_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список участников", callback_data=f"list_{event_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{event_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{event_id}")],
    ])
    return keyboard


def get_admin_list_keyboard(event_id, participants):
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я в деле", callback_data=f"join_{event_id}")],
        [InlineKeyboardButton(text="💳 Оплатил", callback_data=f"paid_{event_id}")],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{event_id}")],
    ])
    return keyboard


def get_topics_keyboard(event_id):
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
# Выбор НАПРАВЛЕНИЯ при создании события
# ============================================================

def get_directions_keyboard(directions):
    """
    Клавиатура выбора направления.
    directions: список кортежей (id, name, is_default) из db.get_directions()
    """
    buttons = []
    for dir_id, name, is_default in directions:
        label = name if len(name) <= 40 else name[:37] + "..."
        prefix = "⭐ " if is_default else "🏐 "
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"direction_pick_{dir_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✏️ Ввести направление вручную", callback_data="direction_manual")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# Выбор АДРЕСА при создании события
# ============================================================

def get_addresses_keyboard(addresses, default_address=None):
    buttons = []
    for addr_id, address, is_default in addresses:
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
# Выбор ВРЕМЕНИ НАЧАЛА при создании события
# ============================================================

def get_start_times_keyboard(start_times):
    buttons = []
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
# Админ-меню управления библиотеками
# ============================================================

def get_settings_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏐 Направления", callback_data="manage_directions")],
        [InlineKeyboardButton(text="📍 Адреса", callback_data="manage_addresses")],
        [InlineKeyboardButton(text="🕐 Время начала", callback_data="manage_start_times")],
        [InlineKeyboardButton(text="⏱ Длительность", callback_data="manage_durations")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ])
    return keyboard


# --- Управление НАПРАВЛЕНИЯМИ ---

def get_directions_management_keyboard(directions):
    buttons = []
    for dir_id, name, is_default in directions:
        label = name if len(name) <= 35 else name[:32] + "..."
        prefix = "⭐" if is_default else "🏐"
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix} {label}",
                callback_data=f"direction_info_{dir_id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"direction_del_{dir_id}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить направление", callback_data="direction_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_direction_info_keyboard(direction_id, is_default):
    buttons = []
    if not is_default:
        buttons.append([
            InlineKeyboardButton(
                text="⭐ Сделать основным",
                callback_data=f"direction_set_default_{direction_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить направление",
            callback_data=f"direction_del_{direction_id}"
        )
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 К списку направлений", callback_data="manage_directions")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Управление АДРЕСАМИ ---

def get_address_management_keyboard(addresses):
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


# --- Управление ВРЕМЕНАМИ НАЧАЛА ---

def get_start_times_management_keyboard(start_times):
    buttons = []
    for time_id, time_str in start_times:
        buttons.append([
            InlineKeyboardButton(
                text=f"🕐 {time_str}",
                callback_data=f"start_time_info_{time_id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"start_time_del_{time_id}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить время", callback_data="start_time_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Управление ДЛИТЕЛЬНОСТЯМИ ---

def get_durations_management_keyboard(durations):
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

# ============================================================
# КАЛЕНДАРЬ (для выбора даты)
# ============================================================

from aiogram_calendar import SimpleCalendar


async def get_calendar_keyboard():
    """
    Возвращает inline-клавиатуру с календарём (русская локаль).
    Используется на шаге выбора даты события.
    """
    return await SimpleCalendar(locale='ru_RU').start_calendar()
