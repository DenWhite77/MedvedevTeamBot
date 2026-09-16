"""
Модуль handlers/admin.py

Содержит обработчики для администраторов:
- Создание события (/new_event)
- Отмена диалога (/cancel)
- Публикация в топики (publish_event)
- Отладка топиков (/topic_id)
- Выписка участников (list_, remove_)
- Отмена через inline-кнопку (cancel)
- Пропуск комментария (skip)
- Удаление событий (delete_event_list, delete_)
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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from config import GROUP_ID
from config import TOPICS

from db import create_event
from db import get_event
from db import get_event_message_id
from db import confirm_payment, remove_participant, get_participants
from db import mark_event_published, is_event_published
from db import delete_event as db_delete_event
from db import get_all_events

from keyboards import get_cancel_keyboard, get_skip_keyboard, get_main_menu
from keyboards import get_publish_keyboard, get_event_keyboard, get_admin_list_keyboard
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


# ============================================================
# СОЗДАНИЕ СОБЫТИЯ
# ============================================================

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


@router.message(NewEventStates.direction)
async def process_direction(message: Message, state: FSMContext):
    """Приём направления."""
    await state.update_data(direction=message.text)
    await message.answer(
        "📍 Введите место проведения:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.place)


@router.message(NewEventStates.place)
async def process_place(message: Message, state: FSMContext):
    """Приём места."""
    await state.update_data(place=message.text)
    await message.answer(
        "📅 Введите дату (например, «17 сентября 2026»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.date)


@router.message(NewEventStates.date)
async def process_date(message: Message, state: FSMContext):
    """Приём даты."""
    await state.update_data(date=message.text)
    await message.answer(
        "🕐 Введите время (например, «20:00–22:00»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.time)


@router.message(NewEventStates.time)
async def process_time(message: Message, state: FSMContext):
    """Приём времени."""
    await state.update_data(time=message.text)
    await message.answer(
        "👥 Введите максимальное количество участников (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NewEventStates.max_participants)


@router.message(NewEventStates.max_participants)
async def process_max_participants(message: Message, state: FSMContext):
    """Приём макс. участников."""
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
    await state.update_data(payment_info=message.text)
    await message.answer(
        "📝 Введите комментарий (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(NewEventStates.comment)


@router.message(NewEventStates.comment)
async def process_comment(message: Message, state: FSMContext):
    """Приём комментария."""
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
        summary,
        parse_mode="Markdown",
        reply_markup=get_publish_keyboard(event_id)
    )

    await message.answer(
        f"✅ Событие создано! ID: `{event_id}`.\n"
        f"Теперь его можно опубликовать в группе.",
        parse_mode="Markdown"
    )

    await state.clear()


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена любого диалога через команду."""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


@router.callback_query(F.data == "skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    """Пропуск шага комментария через inline-кнопку."""
    current_state = await state.get_state()

    if current_state == NewEventStates.comment:
        await state.update_data(comment="")

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
            f"📝 *Комментарий:* —\n\n"
            f"Всё верно? Нажмите «Опубликовать» или «Отмена»."
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
            comment=""
        )

        await callback.message.answer(
            summary,
            parse_mode="Markdown",
            reply_markup=get_publish_keyboard(event_id)
        )

        await callback.message.answer(
            f"✅ Событие создано! ID: `{event_id}`.\n"
            f"Теперь его можно опубликовать в группе.",
            parse_mode="Markdown"
        )

        await state.clear()
        await callback.answer()
    else:
        await callback.answer("⚠️ Кнопка доступна только на шаге комментария.", show_alert=True)


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена диалога через inline-кнопку."""
    await state.clear()
    await callback.message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ============================================================
# ПУБЛИКАЦИЯ В ТОПИКИ
# ============================================================

@router.callback_query(F.data.startswith("publish_event_"))
async def publish_event(callback: CallbackQuery, bot: Bot):
    """Показывает выбор топика для публикации."""
    event_id = int(callback.data.split("_")[2])

    await callback.message.answer(
        "📤 Куда опубликовать событие?\n\n"
        "Выберите топик:",
        reply_markup=get_topics_keyboard(event_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topic_"))
async def publish_to_topic(callback: CallbackQuery, bot: Bot):
    """Публикует событие в выбранный топик."""
    parts = callback.data.split("_")
    topic_key = parts[1]
    event_id = int(parts[2])

    topic = TOPICS.get(topic_key)
    if not topic:
        await callback.answer("⚠️ Топик не найден.", show_alert=True)
        return

    if is_event_published(event_id):
        await callback.answer("⚠️ Это событие уже опубликовано!", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

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
        if topic["thread_id"] is None:
            sent = await bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        else:
            sent = await bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic["thread_id"],
                text=text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )

        logger.info(
            f"=== ПУБЛИКАЦИЯ ===\n"
            f"event_id={event_id}\n"
            f"topic={topic}\n"
            f"GROUP_ID={GROUP_ID}\n"
            f"sent.message_id={sent.message_id}\n"
            f"sent.chat.id={sent.chat.id}\n"
            f"sent.message_thread_id={getattr(sent, 'message_thread_id', None)}"
        )

        mark_event_published(event_id, topic["thread_id"], sent.message_id)

        await callback.message.answer(
            f"✅ Событие опубликовано в топик {topic['name']}!"
        )

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось убрать кнопку: {e}")

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


# ============================================================
# ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ ОПЛАТЫ
# ============================================================

@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: CallbackQuery, bot: Bot):
    """Админ подтверждает оплату — участник переходит в основной состав."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    user_id = int(parts[3])

    confirm_payment(event_id, user_id)
    await callback.message.answer("✅ Оплата подтверждена!")

    from handlers.user import format_event_message
    event = get_event(event_id)
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)

    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")

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


# ============================================================
# СПИСОК УЧАСТНИКОВ И ВЫПИСКА
# ============================================================

@router.callback_query(F.data.startswith("list_"))
async def list_participants(callback: CallbackQuery, bot: Bot):
    """Показывает админу список участников с кнопками выписки."""
    event_id = int(callback.data.split("_")[1])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    participants = get_participants(event_id)
    if not participants:
        await callback.answer("⚠️ Пока никто не записался.", show_alert=True)
        return

    await callback.message.answer(
        f"📋 *Список участников события:*\n"
        f"📅 {event[1]}\n\n"
        f"Нажмите «❌ Выписать», чтобы удалить участника.",
        parse_mode="Markdown",
        reply_markup=get_admin_list_keyboard(event_id, participants)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_"))
async def remove_participant_handler(callback: CallbackQuery, bot: Bot):
    """Админ выписывает участника."""
    parts = callback.data.split("_")
    event_id = int(parts[1])
    user_id = int(parts[2])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    remove_participant(event_id, user_id)
    await callback.answer("✅ Участник выписан.")

    from handlers.user import format_event_message
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)

    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="Markdown",
                reply_markup=get_event_keyboard(event_id)
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")

    try:
        await callback.message.edit_text(
            text=(
                f"📋 *Список участников события:*\n"
                f"📅 {event[1]}\n\n"
                f"Нажмите «❌ Выписать», чтобы удалить участника."
            ),
            parse_mode="Markdown",
            reply_markup=get_admin_list_keyboard(event_id, participants)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить список: {e}")


@router.callback_query(F.data == "edit_event_list")
async def edit_event_list(callback: CallbackQuery, bot: Bot):
    """Показывает список событий для редактирования (заглушка)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    await callback.message.answer(
        "✏️ Редактирование событий — функция в разработке."
    )
    await callback.answer()


@router.callback_query(F.data == "delete_event_list")
async def delete_event_list(callback: CallbackQuery, bot: Bot):
    """Показывает список событий для удаления."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    events = get_all_events()
    if not events:
        await callback.message.answer("⚠️ Нет активных событий.")
        await callback.answer()
        return

    buttons = []
    for event in events:
        event_id = event[0]
        title = event[1]
        date = event[4]
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {title} — {date}",
                callback_data=f"delete_{event_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Закрыть", callback_data="close_list")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        "🗑 *Выберите событие для удаления:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_") & ~F.data.startswith("delete_event_list"))
async def delete_event(callback: CallbackQuery, bot: Bot):
    """Удаляет событие из БД (вместе с участниками) и сообщение из группы."""
    event_id = int(callback.data.split("_")[1])

    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    # Достаём message_id ДО удаления
    message_id = get_event_message_id(event_id)

    # 1. Удаляем сообщение из группы (не блокирует удаление из БД)
    if message_id:
        try:
            await bot.delete_message(
                chat_id=GROUP_ID,
                message_id=message_id
            )
            logger.info(f"Сообщение {message_id} удалено из группы.")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение из группы: {e}")

    # 2. Удаляем из БД (вместе с участниками — см. db.delete_event)
    ok = db_delete_event(event_id)

    if ok:
        await callback.message.answer(f"🗑 Событие ID={event_id} удалено.")
    else:
        await callback.message.answer(
            f"⚠️ Событие ID={event_id} не найдено в БД (возможно, уже удалено)."
        )

    await callback.answer()


@router.callback_query(F.data == "close_list")
async def close_list(callback: CallbackQuery):
    """Закрывает список (удаляет сообщение)."""
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    await callback.answer()
