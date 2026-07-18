import sqlite3

# connect to database
conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

print("=== Daily Output Entry ===")

date = input("Enter date (YYYY-MM-DD): ")
worker_name = input("Enter worker name: ")
loom_number = int(input("Enter loom number: "))
shift = input("Enter shift (Morning/Night): ")
output_quantity = int(input("Enter output quantity: "))

# insert into daily_output table
cursor.execute("""
INSERT INTO daily_output
(date, worker_name, loom_number, shift, output_quantity)
VALUES (?, ?, ?, ?, ?)
""", (date, worker_name, loom_number, shift, output_quantity))

conn.commit()
conn.close()

print("Daily output saved successfully")
