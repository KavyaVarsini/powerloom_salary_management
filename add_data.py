import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# add worker
cursor.execute(
    "INSERT OR IGNORE INTO workers VALUES (?, ?, ?)",
    ("Kavyaa", "9488722250", "Active")
)

# add another worker
cursor.execute(
    "INSERT OR IGNORE INTO workers VALUES (?, ?, ?)",
    ("Jothees", "9123456780", "Active")
)

# add looms
cursor.execute(
    "INSERT OR IGNORE INTO looms VALUES (?, ?)",
    (101, 5.0)
)

cursor.execute(
    "INSERT OR IGNORE INTO looms VALUES (?, ?)",
    (102, 6.5)
)

conn.commit()
conn.close()

print("Workers and looms added successfully")
