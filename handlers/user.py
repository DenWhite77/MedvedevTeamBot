"""
Модуль handlers/user.py

Содержит обработчики для участников:
- Запись на событие (кнопка «Я в деле»)
- Отмена записи
- Отметка «Оплатил»
- Списания с кошелька и выбор мест (+1, +2)
"""
import logging
import sqlite3
from urllib.parse import quote

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LinkPreviewOptions

from config import ADMIN_IDS, GROUP_ID
from db import (
    get_event, get_event_message_id, add_participant, get_participants,
    remove_participant, mark_paid, get_participant_status, get_connection,
)
from keyboards import (
    get_event_keyboard, get_payment_confirm_keyboard,
    get_guests_keyboard, get_payment_type_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="user")


def format_event_message(event, participants):
    """Формирует текст сообщения с событием и списком участников (HTML)."""
    direction = event[1]
    place = event[3]
    date = event[4]
    time = event[5]
    max_participants = event[6]
    price = event[7]
    payment_info = event[8]
    comment = event[9] or "—"

    yandex_link = f'\n🗺 <a href="https://yandex.ru/maps/?text={quote(place)}">Открыть на Яндекс.Картах</a>'

    main_list = []
    reserve_list = []
    total_slots_taken = 0

    for p in participants:
        user_id = p[0]
        username = p[1]
        full_name = p[2]
        status = p[3]
        paid = p[4]
        additional_players = p[5] if len(p) > 5 else 0

        name = full_name or username or f"id{user_id}"

        friends_suffix = f" (+{additional_players})" if additional_players > 0 else ""
        link = f'<a href="tg://user?id={user_id}">{name}</a>{friends_suffix}'
        if username:
            link += f' (@{username})'

        marker = " 💳" if paid == 1 else ""
        count_increment = 1 + additional_players

        if status == "main":
            main_list.append(f"✅ {link}{marker}")
            total_slots_taken += count_increment
        else:
            reserve_list.append(f"🕐 {link}{marker}")

    text = (
        f"📅 <b>{direction}</b>\n\n"
        f"📍 <b>Место:</b> {place}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"🕐 <b>Время:</b> {time}\n"
        f"👥 <b>Макс. участников:</b> {max_participants}\n"
        f"💰 <b>Стоимость:</b> {price} ₽\n"
        f"💳 <b>Оплата:</b> {payment_info}\n"
        f"📝 <b>Комментарий:</b> {comment}"
        f"{yandex_link}\n\n"
    )

    if main_list:
        text += f"<b>Основной состав ({total_slots_taken} из {max_participants}):</b>\n" + "\n".join(main_list) + "\n\n"
    if reserve_list:
        text += f"<b>Резерв ({len(reserve_list)}):</b>\n" + "\n".join(reserve_list) + "\n\n"
    if not main_list and not reserve_list:
        text += "<i>Пока никто не записался.</i>\n\n"

    text += "Нажмите «✅ Я в деле», чтобы записаться!"
    return text


@router.callback_query(F.data.startswith("join_"))
async def join_event(callback: CallbackQuery, bot: Bot):
    """Запись в резерв (без выбора мест)."""
    event_id = int(callback.data.split("_")[1])
    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    user = callback.from_user
    success = add_participant(event_id, user.id, user.username or "", user.full_name or "")
    if not success:
        await callback.answer("⚠️ Вы уже записаны на это событие!", show_alert=True)
        return

    await callback.answer("✅ Вы в резерве!")

    # Обновляем список в группе
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message: {e}")


@router.callback_query(F.data.startswith("slots_"))
@router.callback_query(F.data.startswith("slots_"))
async def process_slots_selection(callback: CallbackQuery, bot: Bot):
    """Шаг 2: Игрок выбрал количество мест. Показываем кнопку оплаты."""
    parts = callback.data.split("_")
    event_id = int(parts[1])
    additional_players = int(parts[2])

    event = get_event(event_id)
    if not event:
        await callback.message.edit_text("⚠️ Событие не найдено.")
        return

    price = event[7]
    total_people = 1 + additional_players
    total_cost = price * total_people

    # Показываем ЛС с кнопкой оплаты
    await callback.message.edit_text(
        f"📅 <b>Событие:</b> {event[1]}\n"
        f"👥 <b>Мест:</b> {total_people} (Вы {f'+ {additional_players} гост.' if additional_players > 0 else 'один'})\n"
        f"💰 <b>Сумма:</b> {total_cost} ₽\n\n"
        f"Нажмите «💰 Оплатить из кошелька», чтобы списать средства с депозита.",
        parse_mode="HTML",
        reply_markup=get_payment_type_keyboard(event_id, additional_players)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("paid_"))
async def paid_event(callback: CallbackQuery, bot: Bot):
    """Участник сообщает, что оплатил (по карте)."""
    event_id = int(callback.data.split("_")[1])

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    user = callback.from_user
    status, paid = get_participant_status(event_id, user.id)

    if status is None:
        await callback.answer("⚠️ Сначала нажмите «✅ Я в деле», чтобы записаться!", show_alert=True)
        return

    if paid == 1:
        await callback.answer("✅ Оплата уже на рассмотрении.", show_alert=True)
        return

    mark_paid(event_id, user.id)
    await callback.answer("✅ Спасибо! Админ проверит оплату.")
    logger.info(f"User {user.id} marked paid for event {event_id}.")

    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message after paid: {e}")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💳 *{user.full_name}* сообщил, что оплатил:\n\n"
                    f"📅 *{event[1]}*\n"
                    f"💰 Стоимость: {event[7]} ₽\n"
                    f"📍 {event[3]}\n"
                    f"📅 {event[4]} в {event[5]}\n\n"
                    f"Подтвердить оплату?"
                ),
                parse_mode="Markdown",
                reply_markup=get_payment_confirm_keyboard(event_id, user.id)
            )
        except Exception as e:
            logger.warning(f"Cannot notify admin {admin_id}: {e}")


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_event(callback: CallbackQuery, bot: Bot):
    """Отмена записи с возвратом на депозит при оплате."""
    event_id = int(callback.data.split("_")[1])

    event = get_event(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено.", show_alert=True)
        return

    user = callback.from_user

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paid, additional_players 
            FROM participants 
            WHERE event_id = ? AND user_id = ?
        """, (event_id, user.id))
        row = cursor.fetchone()

        if not row:
            await callback.answer("⚠️ Вы не записаны на это событие.", show_alert=True)
            return

        paid_status, additional_players = row

    refund_text = ""

    if paid_status == 1:
        price = event[7]
        total_people = 1 + additional_players
        refund_amount = price * total_people

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (user.id,))
            wallet_row = cursor.fetchone()

            if wallet_row is None:
                current_balance = refund_amount
                cursor.execute("""
                    INSERT INTO user_wallets (user_id, username, full_name, balance)
                    VALUES (?, ?, ?, ?)
                """, (user.id, user.username, user.full_name, current_balance))
            else:
                current_balance = wallet_row[0] + refund_amount
                cursor.execute("""
                    UPDATE user_wallets SET balance = ? WHERE user_id = ?
                """, (current_balance, user.id))

            cursor.execute("""
                INSERT INTO wallet_transactions (user_id, amount, type, comment)
                VALUES (?, ?, 'deposit', ?)
            """, (user.id, refund_amount, f"Возврат за отмену игры ID {event_id} ({total_people} чел.)"))

            conn.commit()

        refund_text = f"\n\n💰 <b>Возврат средств:</b> {refund_amount} ₽ возвращены на ваш депозит.\n💳 <b>Текущий баланс:</b> {current_balance:,.2f} ₽"

    remove_participant(event_id, user.id)
    await callback.answer("✅ Запись успешно отменена.")
    logger.info(f"User {user.id} cancelled registration. Refund processed: {paid_status == 1}")

    try:
        await bot.send_message(
            chat_id=user.id,
            text=f"❌ Вы отменили запись на событие <b>{event[1]}</b>.\n\n"
                 f"📅 {event[4]} в {event[5]}\n"
                 f"📍 {event[3]}{refund_text}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Cannot send DM: {e}")

    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Cannot edit message: {e}")


@router.callback_query(F.data.startswith("pay_group_wallet_"))
async def process_group_wallet_payment(callback: CallbackQuery, bot: Bot):
    """Кнопка «💰 Оплатить из кошелька» — отправляем в ЛС выбор мест."""
    event_id = int(callback.data.split("_")[3])
    user = callback.from_user

    status, paid = get_participant_status(event_id, user.id)
    if status is None:
        await callback.answer("⚠️ Сначала нажмите «✅ Я в деле», чтобы записаться!", show_alert=True)
        return

    if paid == 1:
        await callback.answer("✅ У вас уже оплачено это событие!", show_alert=True)
        return

    event = get_event(event_id)
    try:
        await bot.send_message(
            chat_id=user.id,
            text=f"🏐 <b>{event[1]}</b> ({event[4]})\n\n"
                 f"Укажите, сколько мест вы хотите занять (вы + друзья):",
            parse_mode="HTML",
            reply_markup=get_guests_keyboard(event_id)
        )
        await callback.answer("Перевёл в ЛС для выбора мест! 😉")
    except Exception:
        await callback.answer("⚠️ Откройте бота в ЛС и нажмите /start.", show_alert=True)


@router.callback_query(F.data.startswith("pay_wallet_"))
async def process_wallet_payment(callback: CallbackQuery, bot: Bot):
    """Списание с кошелька (вызывается из ЛС)."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    additional_players = int(parts[3])

    event = get_event(event_id)
    price = event[7]
    total_people = 1 + additional_players
    total_cost = price * total_people
    user = callback.from_user

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (user.id,))
        row = cursor.fetchone()
        balance = row[0] if row else 0.0

        if balance < total_cost:
            await callback.answer("⚠️ Недостаточно средств.", show_alert=True)
            return

        new_balance = balance - total_cost
        cursor.execute("UPDATE user_wallets SET balance = ? WHERE user_id = ?", (new_balance, user.id))
        cursor.execute("""
            INSERT INTO wallet_transactions (user_id, amount, type, comment)
            VALUES (?, ?, 'expense', ?)
        """, (user.id, -total_cost, f"Автооплата игры ID {event_id} за {total_people} чел."))

        try:
            cursor.execute("""
                INSERT INTO participants (event_id, user_id, username, full_name, status, paid, additional_players)
                VALUES (?, ?, ?, ?, 'main', 1, ?)
            """, (event_id, user.id, user.username or "", user.full_name or "", additional_players))
        except sqlite3.IntegrityError:
            cursor.execute("""
                UPDATE participants 
                SET status='main', paid=1, additional_players=? 
                WHERE event_id=? AND user_id=?
            """, (additional_players, event_id, user.id))

        conn.commit()

    # Чек в ЛС
    await callback.message.edit_text(
        f"✅ <b>Оплачено!</b>\n\n"
        f"💰 Списано: {total_cost} ₽\n"
        f"💳 Остаток: <b>{new_balance:,.2f} ₽</b>\n\n"
        f"Вы в <b>основном составе</b>. До встречи! 🏐",
        parse_mode="HTML"
    )
    await callback.answer()

    # Обновляем список в группе
    participants = get_participants(event_id)
    new_text = format_event_message(event, participants)
    message_id = get_event_message_id(event_id)
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event_id),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logger.warning(f"Ошибка обновления поста игры: {e}")


@router.callback_query(F.data.startswith("pay_card_"))
async def process_card_payment_request(callback: CallbackQuery, bot: Bot):
    """Оплата картой — ЛС с реквизитами, без сообщений в группе."""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    additional_players = int(parts[3])

    event = get_event(event_id)
    price = event[7]
    user = callback.from_user

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO participants (event_id, user_id, username, full_name, status, paid, additional_players)
                VALUES (?, ?, ?, ?, 'reserve', 0, ?)
            """, (event_id, user.id, user.username or "", user.full_name or "", additional_players))
            conn.commit()
        except sqlite3.IntegrityError:
            cursor.execute("""
                UPDATE participants 
                SET additional_players=? 
                WHERE event_id=? AND user_id=?
            """, (additional_players, event_id, user.id))
            conn.commit()

    # ЛС с реквизитами
    await callback.message.edit_text(
        f"📋 <b>Заявка создана!</b>\n\n"
        f"Для завершения переведите оплату по реквизитам:\n"
        f"👉 <code>{event[8]}</code>\n\n"
        f"После перевода нажмите «💳 Оплатил» в группе, и админ подтвердит вашу заявку.",
        parse_mode="HTML"
    )
    await callback.answer()

    # Уведомление админам (в ЛС)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"💳 <b>{user.full_name}</b> хочет записаться через карту:\n"
                     f"📅 Игра: {event[1]}\n"
                     f"👥 Состав: Он + {additional_players} друзей.\n"
                     f"💰 К оплате: {price * (1 + additional_players)} ₽.",
                parse_mode="HTML",
                reply_markup=get_payment_confirm_keyboard(event_id, user.id)
            )
        except Exception:
            pass
