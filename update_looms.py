import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# Add status column if not exists
try:
    cursor.execute("ALTER TABLE looms ADD COLUMN status TEXT DEFAULT 'Active'")
except:
    pass  # column already exists

conn.commit()
conn.close()

print("Loom table updated")
