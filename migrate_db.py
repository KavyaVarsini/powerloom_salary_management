import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE daily_output ADD COLUMN run_time_hours REAL DEFAULT 12.0")
    print("Database column run_time_hours added successfully.")
except sqlite3.OperationalError as e:
    print("Column run_time_hours already exists or error occurred:", e)

conn.commit()
conn.close()
