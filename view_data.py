import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

print("Workers:")
for row in cursor.execute("SELECT * FROM workers"):
    print(row)

print("\nLooms:")
for row in cursor.execute("SELECT * FROM looms"):
    print(row)

conn.close()
