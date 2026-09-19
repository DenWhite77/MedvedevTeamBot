"""
Модуль db.py

Отвечает за работу с базой данных SQLite.
Содержит функции для создания событий, добавления участников,
работы с библиотеками: адреса, направления, время начала, длительности.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = "events.db"


def get_connection():
    """Возвращает подключение к БД с включёнными foreign_keys."""
    conn = sqlite3.connect(DB_PATH)
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

        # Таблица адресов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Таблица направлений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS directions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_default INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Таблица времён начала
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS start_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Таблица длительностей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS durations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hours INTEGER NOT NULL UNIQUE,
                label TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

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
        logger.info("Added default address.")

    # Дефолтные направления
    cursor.execute("SELECT COUNT(*) FROM directions;")
    if cursor.fetchone()[0] == 0:
        default_directions = [
            ("Волейбол классический", 1, 1),
            ("Волейбол пляжный", 0, 2),
            ("Падл", 0, 3),
        ]
        cursor.executemany("""
            INSERT INTO directions (name, is_default, sort_order)
            VALUES (?, ?, ?)
        """, default_directions)
        logger.info("Added default directions.")

    # Дефолтные времена начала
    cursor.execute("SELECT COUNT(*) FROM start_times;")
    if cursor.fetchone()[0] == 0:
        default_times = [
            ("18:00", 1),
            ("19:00", 2),
            ("20:00", 3),
            ("21:00", 4),
        ]
        cursor.executemany("""
            INSERT INTO start_times (time, sort_order) VALUES (?, ?)
        """, default_times)
        logger.info("Added default start times.")

    # Дефолтные длительности
    cursor.execute("SELECT COUNT(*) FROM durations;")
    if cursor.fetchone()[0] == 0:
        default_durations = [
            (1, "1 час", 1),
            (2, "2 часа", 2),
            (3, "3 часа", 3),
        ]
        cursor.executemany("""
            INSERT INTO durations (hours, label, sort_order) VALUES (?, ?, ?)
        """, default_durations)
        logger.info("Added default durations.")


# ============================================================
# СОБЫТИЯ
# ============================================================

def create_event(title, direction, place, date, time, max_participants, price, payment_info, comment):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, direction, place, date, time, max_participants, price, payment_info, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, direction, place, date, time, max_participants, price, payment_info, comment))
        conn.commit()
        return cursor.lastrowid


def get_event(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return cursor.fetchone()


def get_event_message_id(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message_id FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return row[0] if row else None


def get_all_events():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE status = 'active' ORDER BY date, time")
        return cursor.fetchall()


def mark_event_published(event_id, thread_id, message_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET published = 1, thread_id = ?, message_id = ?
            WHERE id = ?
        """, (thread_id, message_id, event_id))
        conn.commit()


def is_event_published(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT published FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return row and row[0] == 1


def delete_event(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants WHERE event_id = ?", (event_id,))
        participants_deleted = cursor.rowcount
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        event_deleted = cursor.rowcount
        conn.commit()
        if event_deleted == 0:
            logger.warning(f"Event {event_id} not found for deletion.")
            return False
        logger.info(f"Event {event_id} deleted. Participants deleted: {participants_deleted}.")
        return True


# ============================================================
# УЧАСТНИКИ
# ============================================================

def add_participant(event_id, user_id, username, full_name):
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
                logger.warning(f"User {user_id} already registered for event {event_id}.")
                return False
            logger.error(f"IntegrityError without real record: event={event_id}, user={user_id}.")
            return False


def mark_paid(event_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE participants SET paid = 1 WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def confirm_payment(event_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE participants SET status = 'main' WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def get_participants(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, status, paid
            FROM participants WHERE event_id = ?
            ORDER BY status DESC, id ASC
        """, (event_id,))
        return cursor.fetchall()


def remove_participant(event_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM participants WHERE event_id = ? AND user_id = ?
        """, (event_id, user_id))
        conn.commit()


def add_to_main(event_id, user_id):
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, address, is_default
            FROM addresses
            ORDER BY is_default DESC, id ASC
        """)
        return cursor.fetchall()


def get_default_address():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT address FROM addresses WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None


def add_address(address, is_default=False):
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
            logger.warning(f"Address already exists: {address}")
            return None


def delete_address(address_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM addresses WHERE id = ?", (address_id,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted == 0:
            logger.warning(f"Address {address_id} not found for deletion.")
            return False
        return True


def set_default_address(address_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE addresses SET is_default = 0;")
        cursor.execute("UPDATE addresses SET is_default = 1 WHERE id = ?", (address_id,))
        conn.commit()


# ============================================================
# БИБЛИОТЕКА НАПРАВЛЕНИЙ
# ============================================================

def get_directions():
    """Возвращает список направлений, дефолтное — первым."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, is_default
            FROM directions
            ORDER BY is_default DESC, sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def get_default_direction():
    """Возвращает направление по умолчанию (или None)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM directions WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None


def add_direction(name, is_default=False, sort_order=100):
    """Добавляет направление в библиотеку."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_default:
                cursor.execute("UPDATE directions SET is_default = 0;")
            cursor.execute("""
                INSERT INTO directions (name, is_default, sort_order)
                VALUES (?, ?, ?)
            """, (name, 1 if is_default else 0, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Direction already exists: {name}")
            return None


def delete_direction(direction_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM directions WHERE id = ?", (direction_id,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted == 0:
            logger.warning(f"Direction {direction_id} not found for deletion.")
            return False
        return True


def set_default_direction(direction_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE directions SET is_default = 0;")
        cursor.execute("UPDATE directions SET is_default = 1 WHERE id = ?", (direction_id,))
        conn.commit()


# ============================================================
# ВРЕМЯ НАЧАЛА
# ============================================================

def get_start_times():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, time FROM start_times
            ORDER BY sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def add_start_time(time: str, sort_order: int = 100):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO start_times (time, sort_order) VALUES (?, ?)
            """, (time, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Start time already exists: {time}")
            return None


def delete_start_time(time_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM start_times WHERE id = ?", (time_id,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted > 0


# ============================================================
# ДЛИТЕЛЬНОСТЬ
# ============================================================

def get_durations():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, hours, label FROM durations
            ORDER BY sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def add_duration(hours: int, label: str, sort_order: int = 100):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO durations (hours, label, sort_order) VALUES (?, ?, ?)
            """, (hours, label, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Duration already exists: {hours}")
            return None


def delete_duration(duration_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM durations WHERE id = ?", (duration_id,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted > 0


# ============================================================
# УТИЛИТА: РАСЧЁТ ВРЕМЕНИ ОКОНЧАНИЯ
# ============================================================

def calculate_end_time(start_time: str, duration_hours: int) -> str:
    """20:00 + 2 → 22:00"""
    try:
        h, m = map(int, start_time.split(":"))
        total = h * 60 + m + duration_hours * 60
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"
    except Exception as e:
        logger.error(f"calculate_end_time error: start={start_time}, dur={duration_hours}, err={e}")
        return "??:??"
