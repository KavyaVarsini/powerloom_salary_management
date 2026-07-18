import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

cursor.execute("""
SELECT worker_name, date, output_quantity
FROM daily_output
ORDER BY date
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
