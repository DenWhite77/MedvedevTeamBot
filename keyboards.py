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
    """Главное меню для администраторов."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Создать событие", callback_data="new_event")],
        [InlineKeyboardButton(text="✏️ Редактировать событие", callback_data="admin_manage_lists")],
        [InlineKeyboardButton(text="💰 Депозиты участников", callback_data="admin_manage_wallets")],
        [InlineKeyboardButton(text="🗑 Удалить событие", callback_data="delete_event_list")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
    ])
    return keyboard


def get_user_wallet_keyboard():
    """Клавиатура в ЛК/сообщении кошелька для обычного пользователя."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить баланс", callback_data="refresh_wallet")],
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
# Клавиатуры для участников (ВЫБОР МЕСТ + ДЕПОЗИТ)
# ============================================================

def get_guests_keyboard(event_id):
    """Клавиатура выбора количества мест прямо в группе."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Только я", callback_data=f"slots_{event_id}_0")],
        [InlineKeyboardButton(text="👥 +1 друг", callback_data=f"slots_{event_id}_1")],
        [InlineKeyboardButton(text="👥 +2 друга", callback_data=f"slots_{event_id}_2")],
        [InlineKeyboardButton(text="👥 +3 друга", callback_data=f"slots_{event_id}_3")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_payment_type_keyboard(event_id, additional_players):
    """Выбор способа оплаты: картой Лере или с баланса кошелька."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Оплатить из кошелька", callback_data=f"pay_wallet_{event_id}_{additional_players}")],
        [InlineKeyboardButton(text="💳 Обычный перевод на карту", callback_data=f"pay_card_{event_id}_{additional_players}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    return keyboard


def get_event_keyboard(event_id):
    """Клавиатура под анонсом события в канале/чате группы."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я в деле", callback_data=f"join_{event_id}")],
        [
            InlineKeyboardButton(text="💰 Оплатить из кошелька", callback_data=f"pay_group_wallet_{event_id}"),
            InlineKeyboardButton(text="💳 Оплатил (карта)", callback_data=f"paid_{event_id}"),
        ],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{event_id}")],
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
    """Улучшенная клавиатура управления участниками."""
    buttons = []

    if not participants:
        buttons.append([InlineKeyboardButton(text="📭 Список пуст", callback_data="empty_click")])
    else:
        for p in participants:
            user_id, username, full_name, status, paid = p[:5]
            name = full_name or username or f"id{user_id}"

            if status == "main":
                status_marker = "🟢"
                toggle_text = "🟡 В запасной"
                toggle_callback = f"to_reserve_{event_id}_{user_id}"
            else:
                status_marker = "🟡"
                toggle_text = "🟢 В основной"
                toggle_callback = f"to_main_{event_id}_{user_id}"

            name_btn = InlineKeyboardButton(
                text=f"{status_marker} {name}",
                callback_data=f"participant_{event_id}_{user_id}"
            )
            toggle_btn = InlineKeyboardButton(text=toggle_text, callback_data=toggle_callback)
            delete_btn = InlineKeyboardButton(text="❌ Удалить", callback_data=f"remove_{event_id}_{user_id}")

            buttons.append([name_btn])
            buttons.append([toggle_btn, delete_btn])

    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="close_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
        [InlineKeyboardButton(text="💳 Способы оплаты", callback_data="manage_payments")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ])
    return keyboard


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
            text="✏️ Редактировать",
            callback_data=f"addr_edit_{address_id}"
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
    """Возвращает inline-клавиатуру с календарём (русская локаль с fallback)."""
    try:
        return await SimpleCalendar(locale='ru_RU').start_calendar()
    except Exception:
        return await SimpleCalendar().start_calendar()


# ============================================================
# ОПЛАТА: ВЫБОР И УПРАВЛЕНИЕ
# ============================================================

def get_payment_methods_keyboard(methods):
    buttons = []
    for pm_id, name, bank, details, is_default in methods:
        label = name
        if bank:
            label += f" ({bank})"
        if len(label) > 45:
            label = label[:42] + "..."
        prefix = "⭐ " if is_default else "💳 "
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"payment_pick_{pm_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="payment_manual")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_methods_management_keyboard(methods):
    buttons = []
    for pm_id, name, bank, details, is_default in methods:
        label = name
        if bank:
            label += f" ({bank})"
        if len(label) > 35:
            label = label[:32] + "..."
        prefix = "⭐" if is_default else "💳"

        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix} {label}",
                callback_data=f"payment_info_{pm_id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"payment_del_{pm_id}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить способ оплаты", callback_data="payment_add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_method_info_keyboard(method_id, is_default):
    buttons = []
    if not is_default:
        buttons.append([
            InlineKeyboardButton(
                text="⭐ Сделать основным",
                callback_data=f"payment_set_default_{method_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"payment_del_{method_id}"
        )
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 К списку", callback_data="manage_payments")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_wallet_management_keyboard():
    """Меню управления депозитами для Леры."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Начислить / Списать баланс", callback_data="admin_deposit_money")],
        [InlineKeyboardButton(text="📊 Список всех депозитов", callback_data="admin_list_wallets")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")],
    ])
    return keyboard
