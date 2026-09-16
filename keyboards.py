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
# Клавиатуры для админа
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
