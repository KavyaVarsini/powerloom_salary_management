import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

cursor.execute("""
UPDATE daily_output
SET output_quantity = 0
WHERE output_quantity IS NULL
""")

conn.commit()
conn.close()

print("NULL output values fixed successfully.")
