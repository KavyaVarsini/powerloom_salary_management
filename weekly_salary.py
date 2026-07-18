import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

print("=== Weekly Salary Calculation ===")

worker_name = input("Enter worker name: ")
start_date = input("Enter week start date (Sunday) YYYY-MM-DD: ")
end_date = input("Enter week end date (Saturday) YYYY-MM-DD: ")

# SQL query to calculate salary
query = """
SELECT d.date,
       d.output_quantity,
       l.rate_per_unit,
       (d.output_quantity * l.rate_per_unit) AS daily_pay
FROM daily_output d
JOIN looms l ON d.loom_number = l.loom_number
WHERE d.worker_name = ?
AND d.date BETWEEN ? AND ?
"""

cursor.execute(query, (worker_name, start_date, end_date))
records = cursor.fetchall()

total_salary = 0

print("\nDate | Output | Rate | Daily Pay")
print("----------------------------------")

for row in records:
    date, output, rate, daily_pay = row
    total_salary += daily_pay
    print(f"{date} | {output} | {rate} | {daily_pay}")

print("----------------------------------")
print(f"Total Weekly Salary for {worker_name}: ₹{total_salary}")

conn.close()
