"""
Модуль db.py

Отвечает за работу с базой данных SQLite.
Содержит функции для создания событий, добавления участников,
работы с библиотекой адресов и шаблонами времени.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = "events.db"


def get_connection():
    """Возвращает подключение к БД с включёнными foreign_keys."""
    conn = sqlite3.connect(DB_PATH)
    # ВАЖНО: без этой строки ON DELETE CASCADE не работает!
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Создаёт таблицы, если их ещё нет. Заполняет дефолты при первом запуске."""
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

        # Таблица адресов (библиотека)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Таблица шаблонов времени
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                label TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        # Заполняем дефолтами, если таблицы пустые
        _seed_defaults(cursor)
        conn.commit()

        logger.info("База данных инициализирована.")


def _seed_defaults(cursor):
    """Заполняет таблицы дефолтными значениями (только если они пустые)."""

    # Дефолтный адрес
    cursor.execute("SELECT COUNT(*) FROM addresses;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO addresses (address, is_default)
            VALUES (?, 1)
        """, ("ул. Подольских Курсантов, 16-А (Школа № 657)",))
        logger.info("Добавлен дефолтный адрес.")

    # Дефолтные слоты времени
    cursor.execute("SELECT COUNT(*) FROM time_slots;")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("20:00", "22:00", "20:00–22:00 (2ч)", 1),
            ("19:00", "21:00", "19:00–21:00 (2ч)", 2),
            ("18:00", "20:00", "18:00–20:00 (2ч)", 3),
        ]
        cursor.executemany("""
            INSERT INTO time_slots (start_time, end_time, label, sort_order)
            VALUES (?, ?, ?, ?)
        """, defaults)
        logger.info("Добавлены дефолтные слоты времени.")


# ============================================================
# СОБЫТИЯ
# ============================================================

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


def get_event_message_id(event_id):
    """Возвращает message_id опубликованного сообщения события (или None)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message_id FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return row[0] if row else None


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


def delete_event(event_id):
    """
    Полностью удаляет событие и всех его участников.
    Возвращает True, если событие было удалено, иначе False.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM participants WHERE event_id = ?", (event_id,))
        participants_deleted = cursor.rowcount

        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        event_deleted = cursor.rowcount

        conn.commit()

        if event_deleted == 0:
            logger.warning(f"Событие {event_id} не найдено в БД при удалении.")
            return False

        logger.info(
            f"Событие {event_id} удалено. Участников удалено: {participants_deleted}."
        )
        return True


# ============================================================
# УЧАСТНИКИ
# ============================================================

def add_participant(event_id, user_id, username, full_name):
    """
    Добавляет участника в резерв.
    Возвращает True при успехе, False если уже записан.
    """
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
            cursor.execute(
                "SELECT 1 FROM participants WHERE event_id = ? AND user_id = ?",
                (event_id, user_id)
            )
            real = cursor.fetchone()
            if real:
                logger.warning(f"Пользователь {user_id} уже записан на событие {event_id}.")
                return False
            else:
                logger.error(
                    f"IntegrityError без реальной записи: event={event_id}, user={user_id}."
                )
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


# ============================================================
# БИБЛИОТЕКА АДРЕСОВ
# ============================================================

def get_addresses():
    """Возвращает список всех адресов, дефолтный — первым."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, address, is_default
            FROM addresses
            ORDER BY is_default DESC, id ASC
        """)
        return cursor.fetchall()


def get_default_address():
    """Возвращает адрес по умолчанию (или None)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT address FROM addresses WHERE is_default = 1 LIMIT 1
        """)
        row = cursor.fetchone()
        return row[0] if row else None


def add_address(address, is_default=False):
    """
    Добавляет адрес в библиотеку.
    Если is_default=True — снимает флаг с других адресов.
    Возвращает ID нового адреса или None, если такой уже есть.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_default:
                cursor.execute("UPDATE addresses SET is_default = 0;")

            cursor.execute("""
                INSERT INTO addresses (address, is_default)
                VALUES (?, ?)
            """, (address, 1 if is_default else 0))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Адрес уже существует: {address}")
            return None


def delete_address(address_id):
    """Удаляет адрес по ID. Возвращает True при успехе."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM addresses WHERE id = ?", (address_id,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted == 0:
            logger.warning(f"Адрес {address_id} не найден при удалении.")
            return False
        logger.info(f"Адрес {address_id} удалён.")
        return True


def set_default_address(address_id):
    """Делает указанный адрес дефолтным."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE addresses SET is_default = 0;")
        cursor.execute("UPDATE addresses SET is_default = 1 WHERE id = ?", (address_id,))
        conn.commit()
        logger.info(f"Адрес {address_id} установлен как дефолтный.")


# ============================================================
# ШАБЛОНЫ ВРЕМЕНИ
# ============================================================

def get_time_slots():
    """Возвращает список всех шаблонов времени, отсортированных по sort_order."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, start_time, end_time, label
            FROM time_slots
            ORDER BY sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def add_time_slot(start_time, end_time, label, sort_order=100):
    """
    Добавляет шаблон времени.
    Возвращает ID нового слота или None, если такой уже есть.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO time_slots (start_time, end_time, label, sort_order)
                VALUES (?, ?, ?, ?)
            """, (start_time, end_time, label, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Слот уже существует: {label}")
            return None


def delete_time_slot(slot_id):
    """Удаляет шаблон времени по ID. Возвращает True при успехе."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM time_slots WHERE id = ?", (slot_id,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted == 0:
            logger.warning(f"Слот {slot_id} не найден при удалении.")
            return False
        logger.info(f"Слот {slot_id} удалён.")
        return True
