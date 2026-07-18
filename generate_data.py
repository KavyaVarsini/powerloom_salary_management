import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# Fetch actual active workers from db if they exist, otherwise use default list
cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active'")
db_workers = [row[0] for row in cursor.fetchall()]
workers = db_workers if db_workers else [
    "Arun Kumar","Praveen","Sathish","Manikandan","Karthik",
    "Dinesh","Harish","Lokesh","Bharath","Gokul",
    "Vignesh","Deepak","Navin","Vijay","Suresh"
]

# Fetch actual active looms from db if they exist, otherwise use default list
cursor.execute("SELECT loom_number FROM looms WHERE status='Active'")
db_looms = [row[0] for row in cursor.fetchall()]
looms = db_looms if db_looms else [101,102,103,104,105,106,107,108,109,110]

shifts = ["Morning","Night"]

# Set date range relative to today's date
end_date = datetime.now()
start_date = end_date - timedelta(days=14)

records_to_generate = 200

dates = []
current = start_date
while current <= end_date:
    dates.append(current.strftime("%Y-%m-%d"))
    current += timedelta(days=1)

for _ in range(records_to_generate):
    worker = random.choice(workers)
    loom = random.choice(looms)
    shift = random.choice(shifts)
    date = random.choice(dates)
    output = random.randint(80,160)
    run_time = round(random.uniform(8.0, 12.0), 1)

    cursor.execute("""
    INSERT INTO daily_output
    (date, worker_name, loom_number, shift, output_quantity, run_time_hours)
    VALUES (?, ?, ?, ?, ?, ?)
    """,(date,worker,loom,shift,output,run_time))

conn.commit()
conn.close()

print(f"Successfully generated {records_to_generate} mock records relative to today's date ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}).")