"""
Модуль handlers/admin/events/states.py

Состояния FSM для создания события + локализация даты.
Вынесено отдельно, чтобы избежать циклических импортов.
"""
from datetime import datetime

from aiogram.fsm.state import State, StatesGroup


# ============================================================
# ЛОКАЛИЗАЦИЯ ДАТЫ
# ============================================================

WEEKDAYS_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def format_date_ru(date: datetime) -> str:
    """Форматирует дату как «20 сентября 2026 (Воскресенье)»."""
    weekday = WEEKDAYS_RU[date.weekday()]
    month = MONTHS_RU[date.month]
    return f"{date.day} {month} {date.year} ({weekday})"


# ============================================================
# СОСТОЯНИЯ FSM
# ============================================================

class NewEventStates(StatesGroup):
    """Состояния диалога создания события."""
    direction = State()
    direction_manual = State()
    place = State()
    place_manual = State()
    date = State()
    time_start = State()
    time_start_manual = State()
    time_duration = State()
    max_participants = State()
    price = State()
    payment_pick = State()
    payment_manual = State()
    payment_manual_details = State()
    comment = State()
    