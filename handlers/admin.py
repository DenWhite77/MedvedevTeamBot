"""
Модуль handlers/admin.py

Содержит обработчики для администраторов:
- Создание события (/new_event)
- Отмена диалога (/cancel)
- Публикация в топики (publish_event)
- Отладка топиков (/topic_id)
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram import Bot
from aiogram import F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from config import GROUP_ID
from config import TOPICS

from db import create_event
from db import get_event
from db import confirm_payment, remove_participant

from keyboards import get_cancel_keyboard, get_skip_keyboard, get_main_menu
from keyboards import get_publish_keyboard, get_event_keyboard
from keyboards import get_topics_keyboard

logger = logging.getLogger(__name__)

# Роутер для админов
router = Router()


class NewEventStates(StatesGroup):
    """Состояния пошагового диалога создания события."""
    direction = State()
    place = State()
    date = State()
    time = State()
    max_participants = State()
    price = State()
    payment_info = State()
    comment = State()
    confirm = State()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in ADMIN_IDS


@router.message(Command("new_event"))
async def new_event_start(message: Message, state: FSMContext):
    """Старт создания события."""
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


@router.message(NewEventStates.direction)
async def process_direction(message: Message, state: FSMContext):
    """Приём направления."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    await state.update_data(direction=message.text)
    await message.answer(
        "📍 Введите место проведения:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.place)


@router.message(NewEventStates.place)
async def process_place(message: Message, state: FSMContext):
    """Приём места."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    await state.update_data(place=message.text)
    await message.answer(
        "📅 Введите дату (например, «17 сентября 2026»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.date)


@router.message(NewEventStates.date)
async def process_date(message: Message, state: FSMContext):
    """Приём даты."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    await state.update_data(date=message.text)
    await message.answer(
        "🕐 Введите время (например, «20:00–22:00»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.time)


@router.message(NewEventStates.time)
async def process_time(message: Message, state: FSMContext):
    """Приём времени."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    await state.update_data(time=message.text)
    await message.answer(
        "👥 Введите максимальное количество участников (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.max_participants)


@router.message(NewEventStates.max_participants)
async def process_max_participants(message: Message, state: FSMContext):
    """Приём макс. участников."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

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
    """Приём стоимости."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

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
    """Приём способа оплаты."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    await state.update_data(payment_info=message.text)
    await message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)


@router.message(NewEventStates.comment)
async def process_comment(message: Message, state: FSMContext):
    """Приём комментария."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Создание события отменено.", reply_markup=get_main_menu())
        return

    if message.text == "⏭ Пропустить":
        await state.update_data(comment="")
    else:
        await state.update_data(comment=message.text)

    data = await state.get_data()
    summary = (
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

    await message.answer(
        summary,
        parse_mode="Markdown",
        reply_markup=get_publish_keyboard()
    )

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

    await message.answer(
        f"✅ Событие создано! ID: `{event_id}`.\n"
        f"Теперь его можно опубликовать в группе.",
        parse_mode="Markdown"
    )

    await state.clear()


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена любого диалога."""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


@router.callback_query(F.data == "publish_event")
async def publish_event(callback: CallbackQuery, bot: Bot):
    """Показывает выбор топика для публикации."""
    from db import get_all_events
    events = get_all_events()
    if not events:
        await callback.message.answer("⚠️ Нет событий для публикации.")
        await callback.answer()
        return

    await callback.message.answer(
        "📤 Куда опубликовать событие?\n\n"
        "Выберите топик:",
        reply_markup=get_topics_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topic_"))
async def publish_to_topic(callback: CallbackQuery, bot: Bot):
    """Публикует событие в выбранный топик."""
    topic_key = callback.data.replace("topic_", "")
    topic = TOPICS.get(topic_key)

    if not topic:
        await callback.answer("⚠️ Топик не найден.", show_alert=True)
        return

    from db import get_all_events
    events = get_all_events()
    if not events:
        await callback.answer("⚠️ Нет событий для публикации.", show_alert=True)
        return

    event = events[-1]
    event_id = event[0]

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
        # Если топик General (thread_id = None), отправляем без message_thread_id
        if topic["thread_id"] is None:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        else:
            await bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic["thread_id"],
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        await callback.message.answer(
            f"✅ Событие опубликовано в топик {topic['name']}!"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при публикации: {e}")

    await callback.answer()


@router.message(Command("topic_id"))
async def get_topic_id(message: Message):
    """Показывает message_thread_id текущего топика (для отладки)."""
    thread_id = message.message_thread_id
    chat_id = message.chat.id
    await message.answer(
        f"📌 message_thread_id: {thread_id}\n"
        f"chat_id: {chat_id}"
    )


@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: CallbackQuery, bot: Bot):
    """Админ подтверждает оплату — участник переходит в основной состав."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    # Подтверждаем оплату в БД
    confirm_payment(event_id, user_id)

    await callback.message.answer("✅ Оплата подтверждена!")

    # Обновляем сообщение в группе
    from db import get_event, get_participants
    from handlers.user import format_event_message
    event = get_event(event_id)
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)

    try:
        # Находим сообщение с событием в группе (по ID из уведомления)
        # Проще всего — отправить новое сообщение в тот же топик
        await bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=callback.message.message_thread_id,
            text=new_text,
            parse_mode="Markdown",
            reply_markup=get_event_keyboard(event_id)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение в группе: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment_handler(callback: CallbackQuery, bot: Bot):
    """Админ отклоняет оплату — участник выписывается."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    remove_participant(event_id, user_id)
    await callback.message.answer("❌ Участник выписан из события.")
    await callback.answer()


@router.callback_query(F.data == "new_event")
async def new_event_callback(callback: CallbackQuery, state: FSMContext):
    """Старт создания события через кнопку."""
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
