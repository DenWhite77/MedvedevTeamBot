"""Временный скрипт для проверки БД payment_methods."""
import sqlite3

conn = sqlite3.connect("events.db")
c = conn.cursor()

print("=== payment_methods ===")
c.execute("SELECT id, name, bank, details, is_default FROM payment_methods")
for row in c.fetchall():
    print(row)

conn.close()

print("\n=== db.py: содержит 'Наличные'? ===")
with open("db.py", "r", encoding="utf-8") as f:
    content = f.read()

target = "Наличные"
if target in content:
    print(f"ЕСТЬ в db.py:")
    for i, line in enumerate(content.split("\n"), 1):
        if target in line:
            print(f"  {i}: {line.strip()}")
else:
    print("НЕТ в db.py")
