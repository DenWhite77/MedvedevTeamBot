"""
Модуль db.py

Отвечает за работу с базой данных SQLite.
Содержит функции для создания событий, добавления участников и т.д.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = "events.db"


def get_connection():
    """Возвращает подключение к базе данных."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Создаёт таблицы, если их ещё нет."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Таблица событий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                direction TEXT,
                place TEXT,
                date TEXT,
                time TEXT,
                max_participants INTEGER,
                price INTEGER,
                payment_info TEXT,
                comment TEXT,
                status TEXT DEFAULT 'active',
                published INTEGER DEFAULT 0,
                thread_id INTEGER,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Таблица участников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'reserve',
                paid INTEGER DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                UNIQUE (event_id, user_id)
            );
        """)

        conn.commit()
        logger.info("База данных инициализирована.")


def create_event(title, direction, place, date, time, max_participants, price, payment_info, comment):
    """Создаёт новое событие и возвращает его ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, direction, place, date, time, max_participants, price, payment_info, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, direction, place, date, time, max_participants, price, payment_info, comment))
        conn.commit()
        return cursor.lastrowid


def get_event(event_id):
    """Возвращает событие по ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return cursor.fetchone()


def get_all_events():
    """Возвращает список всех активных событий."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE status = 'active' ORDER BY date, time")
        return cursor.fetchall()


def mark_event_published(event_id, thread_id, message_id):
    """Помечает событие как опубликованное + сохраняет thread_id и message_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET published = 1, thread_id = ?, message_id = ?
            WHERE id = ?
        """, (thread_id, message_id, event_id))
        conn.commit()


def is_event_published(event_id):
    """Проверяет, опубликовано ли событие."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT published FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return row and row[0] == 1


def add_participant(event_id, user_id, username, full_name):
    """Добавляет участника в резерв."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO participants (event_id, user_id, username, full_name, status, paid)
                VALUES (?, ?, ?, ?, 'reserve', 0)
            """, (event_id, user_id, username, full_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Пользователь {user_id} уже записан на событие {event_id}.")
            return False


def mark_paid(event_id, user_id):
    """Отмечает участника как оплатившего."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE participants SET paid = 1 WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def confirm_payment(event_id, user_id):
    """Админ подтверждает оплату — участник в основной состав."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE participants SET status = 'main' WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def get_participants(event_id):
    """Возвращает список всех участников события."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, status, paid
            FROM participants WHERE event_id = ?
            ORDER BY status DESC, id ASC
        """, (event_id,))
        return cursor.fetchall()


def remove_participant(event_id, user_id):
    """Удаляет участника из события."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM participants WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def add_to_main(event_id, user_id):
    """Вручную добавляет участника в основной состав."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE participants SET status = 'main', paid = 1
            WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()
