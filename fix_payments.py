"""Одноразовая миграция: правильные дефолты payment_methods."""
import sqlite3

conn = sqlite3.connect("events.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM payment_methods;")

cursor.execute("""
    INSERT INTO payment_methods (name, bank, details, is_default, sort_order)
    VALUES (?, ?, ?, ?, ?)
""", ("Перевод на карту", "Сбербанк или Т-банк", "+79267217588", 1, 1))

cursor.execute("""
    INSERT INTO payment_methods (name, bank, details, is_default, sort_order)
    VALUES (?, ?, ?, ?, ?)
""", ("Наличные", None, None, 0, 2))

conn.commit()

cursor.execute("SELECT id, name, bank, details, is_default FROM payment_methods;")
for row in cursor.fetchall():
    print(row)

conn.close()
