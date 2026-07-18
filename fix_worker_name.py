import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# Fix incorrect worker name
cursor.execute("""
UPDATE daily_output
SET worker_name = 'Kavyaa'
WHERE worker_name = 'Kavya'
""")

conn.commit()

# Verify result
cursor.execute("SELECT DISTINCT worker_name FROM daily_output")
print("Worker names in daily_output:")
for row in cursor.fetchall():
    print(row[0])

conn.close()
