"""Удаление 'Наличные' из payment_methods на сервере."""
import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

# Удаляем 'Наличные'
c.execute("DELETE FROM payment_methods WHERE name = ?", ("Наличные",))
deleted = c.rowcount
conn.commit()

print(f"Удалено записей: {deleted}")

# Проверка
print("\n=== payment_methods после удаления ===")
c.execute("SELECT id, name, bank, details, is_default FROM payment_methods")
for row in c.fetchall():
    print(row)

conn.close()
