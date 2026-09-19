"""
Модуль handlers/admin/common.py

Общие утилиты для админских хендлеров:
- проверка прав администратора
- сборка текста-сводки события
"""
from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in ADMIN_IDS


def build_event_summary(data: dict) -> str:
    """Собирает текст-сводку события для подтверждения."""
    return (
        f"📅 *Событие:*\n\n"
        f"🏐 *Направление:* {data['direction']}\n"
        f"📍 *Место:* {data['place']}\n"
        f"📅 *Дата:* {data['date']}\n"
        f"🕐 *Время:* {data['time']}\n"
        f"👥 *Макс. участников:* {data['max_participants']}\n"
        f"💰 *Стоимость:* {data['price']} ₽\n"
        f"💳 *Оплата:* {data['payment_info']}\n"
        f"📝 *Комментарий:* {data.get('comment', '—')}\n\n"
        f"Всё верно? Нажмите «Опубликовать» или «Отмена»."
    )
