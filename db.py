"""
Модуль db.py

Отвечает за работу с базой данных SQLite.
Содержит функции для создания событий, добавления участников,
работы с библиотеками: адреса (с геокодированием), направления,
время начала, длительности, способы оплаты.
"""
import sqlite3
import logging
import os
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

DB_PATH = "events.db"

# Ключ Яндекс.Геокодера из .env
YANDEX_GEOCODER_API_KEY = os.getenv("YANDEX_GEOCODER_API_KEY", "")


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

        # Таблица адресов (с координатами)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                latitude REAL,
                longitude REAL,
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

        # Таблица способов оплаты
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payment_methods (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        bank TEXT,
                        details TEXT,
                        is_default INTEGER DEFAULT 0,
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (name, bank)
                    );
                """)

        conn.commit()
        _seed_defaults(cursor)
        conn.commit()

        logger.info("База данных инициализирована.")


def _migrate_addresses_columns(cursor):
    """Добавляет колонки latitude/longitude в addresses, если их нет."""
    cursor.execute("PRAGMA table_info(addresses);")
    columns = [row[1] for row in cursor.fetchall()]
    if "latitude" not in columns:
        cursor.execute("ALTER TABLE addresses ADD COLUMN latitude REAL;")
        logger.info("Added column addresses.latitude")
    if "longitude" not in columns:
        cursor.execute("ALTER TABLE addresses ADD COLUMN longitude REAL;")
        logger.info("Added column addresses.longitude")


def _seed_defaults(cursor):
    """Заполняет таблицы дефолтными значениями (только если они пустые)."""

    _migrate_addresses_columns(cursor)

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
            ("18:00", 1), ("19:00", 2), ("20:00", 3), ("21:00", 4),
        ]
        cursor.executemany("""
            INSERT INTO start_times (time, sort_order) VALUES (?, ?)
        """, default_times)
        logger.info("Added default start times.")

    # Дефолтные длительности
    cursor.execute("SELECT COUNT(*) FROM durations;")
    if cursor.fetchone()[0] == 0:
        default_durations = [
            (1, "1 час", 1), (2, "2 часа", 2), (3, "3 часа", 3),
        ]
        cursor.executemany("""
            INSERT INTO durations (hours, label, sort_order) VALUES (?, ?, ?)
        """, default_durations)
        logger.info("Added default durations.")

        # Дефолтные способы оплаты
        cursor.execute("SELECT COUNT(*) FROM payment_methods;")
        if cursor.fetchone()[0] == 0:
            default_payment = [
                ("Перевод на карту", "Сбербанк или Т-банк", "+79267217588", 1, 1),
                ("Наличные", None, None, 0, 2),
            ]
            cursor.executemany("""
                INSERT INTO payment_methods (name, bank, details, is_default, sort_order)
                VALUES (?, ?, ?, ?, ?)
            """, default_payment)
            logger.info("Added default payment methods.")


# ============================================================
# ГЕОКОДЕР
# ============================================================

async def geocode_address(address: str) -> tuple:
    """Геокодирует адрес через Яндекс.Геокодер."""
    if not YANDEX_GEOCODER_API_KEY:
        logger.warning("YANDEX_GEOCODER_API_KEY не задан — геокодирование пропущено.")
        return None, None

    url = (
        f"https://geocode-maps.yandex.ru/1.x/"
        f"?apikey={YANDEX_GEOCODER_API_KEY}"
        f"&geocode={quote(address)}"
        f"&format=json&results=1"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"Geocoder HTTP {resp.status} for '{address}'")
                    return None, None
                data = await resp.json()
                members = (
                    data.get("response", {})
                    .get("GeoObjectCollection", {})
                    .get("featureMember", [])
                )
                if not members:
                    logger.warning(f"Geocoder: no results for '{address}'")
                    return None, None
                pos = members[0]["GeoObject"]["Point"]["pos"]
                lon_str, lat_str = pos.split(" ")
                return float(lat_str), float(lon_str)
    except Exception as e:
        logger.error(f"Geocoder error for '{address}': {e}")
        return None, None


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
            UPDATE events SET published = 1, thread_id = ?, message_id = ?
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
            if cursor.fetchone():
                logger.warning(f"User {user_id} already registered for event {event_id}.")
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
            SELECT id, address, is_default FROM addresses
            ORDER BY is_default DESC, id ASC
        """)
        return cursor.fetchall()


def get_address_full(address_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, address, latitude, longitude, is_default
            FROM addresses WHERE id = ?
        """, (address_id,))
        return cursor.fetchone()


def get_address_coords_by_text(address: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT latitude, longitude FROM addresses WHERE address = ?", (address,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            return row[0], row[1]
        return None, None


def get_default_address():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT address FROM addresses WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None


async def add_address(address: str, is_default: bool = False):
    lat, lon = await geocode_address(address)
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_default:
                cursor.execute("UPDATE addresses SET is_default = 0;")
            cursor.execute("""
                INSERT INTO addresses (address, latitude, longitude, is_default)
                VALUES (?, ?, ?, ?)
            """, (address, lat, lon, 1 if is_default else 0))
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
        return deleted > 0


def set_default_address(address_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE addresses SET is_default = 0;")
        cursor.execute("UPDATE addresses SET is_default = 1 WHERE id = ?", (address_id,))
        conn.commit()


async def migrate_addresses():
    """Одноразовая миграция координат для адресов без lat/lon."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, address FROM addresses WHERE latitude IS NULL OR longitude IS NULL")
        rows = cursor.fetchall()

    if not rows:
        logger.info("Migrate addresses: nothing to do.")
        return

    for addr_id, address in rows:
        lat, lon = await geocode_address(address)
        if lat is not None and lon is not None:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE addresses SET latitude = ?, longitude = ? WHERE id = ?", (lat, lon, addr_id))
                conn.commit()
            logger.info(f"Migrated address id={addr_id}: lat={lat}, lon={lon}")
        else:
            logger.warning(f"Cannot geocode address id={addr_id}: '{address}'")


# ============================================================
# БИБЛИОТЕКА НАПРАВЛЕНИЙ
# ============================================================

def get_directions():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, is_default FROM directions
            ORDER BY is_default DESC, sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def get_default_direction():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM directions WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None


def add_direction(name, is_default=False, sort_order=100):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_default:
                cursor.execute("UPDATE directions SET is_default = 0;")
            cursor.execute("""
                INSERT INTO directions (name, is_default, sort_order) VALUES (?, ?, ?)
            """, (name, 1 if is_default else 0, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def delete_direction(direction_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM directions WHERE id = ?", (direction_id,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted > 0


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
        cursor.execute("SELECT id, time FROM start_times ORDER BY sort_order ASC, id ASC")
        return cursor.fetchall()


def add_start_time(time: str, sort_order: int = 100):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO start_times (time, sort_order) VALUES (?, ?)", (time, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
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
        cursor.execute("SELECT id, hours, label FROM durations ORDER BY sort_order ASC, id ASC")
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
            return None


def delete_duration(duration_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM durations WHERE id = ?", (duration_id,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted > 0


# ============================================================
# БИБЛИОТЕКА СПОСОБОВ ОПЛАТЫ
# ============================================================

def get_payment_methods():
    """Возвращает список: id, name, bank, details, is_default."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, bank, details, is_default FROM payment_methods
            ORDER BY is_default DESC, sort_order ASC, id ASC
        """)
        return cursor.fetchall()


def get_payment_method(method_id: int):
    """Возвращает одну запись: id, name, bank, details, is_default."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, bank, details, is_default
            FROM payment_methods WHERE id = ?
        """, (method_id,))
        return cursor.fetchone()


def get_default_payment_method():
    """Возвращает (name, bank, details) дефолтного способа или (None, None, None)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, bank, details FROM payment_methods
            WHERE is_default = 1 LIMIT 1
        """)
        row = cursor.fetchone()
        return row if row else (None, None, None)


def format_payment_info(name: str, bank: str = None, details: str = None) -> str:
    """
    Формирует текст для поля payment_info:
    "Перевод на карту Сбербанк или Т-банк\n+79267217588"
    """
    line1 = name
    if bank:
        line1 += f" {bank}"
    if details:
        return f"{line1}\n{details}"
    return line1


def add_payment_method(name: str, bank: str = None, details: str = None,
                       is_default: bool = False, sort_order: int = 100):
    """Добавляет способ оплаты. Возвращает ID или None, если такой уже есть."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            if is_default:
                cursor.execute("UPDATE payment_methods SET is_default = 0;")
            cursor.execute("""
                INSERT INTO payment_methods (name, bank, details, is_default, sort_order)
                VALUES (?, ?, ?, ?, ?)
            """, (name, bank, details, 1 if is_default else 0, sort_order))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Payment method already exists: {name} / {bank}")
            return None


def delete_payment_method(method_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payment_methods WHERE id = ?", (method_id,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted > 0


def set_default_payment_method(method_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE payment_methods SET is_default = 0;")
        cursor.execute("UPDATE payment_methods SET is_default = 1 WHERE id = ?", (method_id,))
        conn.commit()


# ============================================================
# УТИЛИТА
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
