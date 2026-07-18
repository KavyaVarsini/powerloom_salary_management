import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE looms ADD COLUMN status TEXT DEFAULT 'Active'")
    print("Status column added to looms table")
except sqlite3.OperationalError as e:
    print("Column may already exist:", e)

conn.commit()
conn.close()
