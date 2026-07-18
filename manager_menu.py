import sqlite3

def connect_db():
    return sqlite3.connect("powerloom.db")
def get_workers():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active'")
    workers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return workers

def get_looms():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT loom_number FROM looms")
    looms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return looms


# 1. Add Worker
def add_worker():
    conn = connect_db()
    cursor = conn.cursor()

    name = input("Enter worker name: ")
    phone = input("Enter phone number: ")
    status = "Active"

    cursor.execute(
        "INSERT OR IGNORE INTO workers VALUES (?, ?, ?)",
        (name, phone, status)
    )

    conn.commit()
    conn.close()
    print("Worker added successfully")

# 2. Add Loom
def add_loom():
    conn = connect_db()
    cursor = conn.cursor()

    loom_number = int(input("Enter loom number: "))
    rate = float(input("Enter rate per unit: "))

    cursor.execute(
        "INSERT OR IGNORE INTO looms VALUES (?, ?)",
        (loom_number, rate)
    )

    conn.commit()
    conn.close()
    print("Loom added successfully")

# 3. Daily Output Entry
def daily_entry():
    conn = connect_db()
    cursor = conn.cursor()

    workers = get_workers()
    looms = get_looms()

    print("Available Workers:", workers)
    worker = input("Enter worker name: ")

    if worker not in workers:
        print("Invalid worker name!")
        conn.close()
        return

    print("Available Loom Numbers:", looms)
    loom = int(input("Enter loom number: "))

    if loom not in looms:
        print("Invalid loom number!")
        conn.close()
        return

    date = input("Enter date (YYYY-MM-DD): ")
    shift = input("Enter shift (Morning/Night): ")

    if shift not in ["Morning", "Night"]:
        print("Invalid shift!")
        conn.close()
        return

    output = int(input("Enter output quantity: "))

    cursor.execute("""
    INSERT INTO daily_output
    (date, worker_name, loom_number, shift, output_quantity)
    VALUES (?, ?, ?, ?, ?)
    """, (date, worker, loom, shift, output))

    conn.commit()
    conn.close()
    print("Daily output saved successfully")


# 4. Weekly Salary Calculation
def weekly_salary():
    conn = connect_db()
    cursor = conn.cursor()

    workers = get_workers()
    print("Available Workers:", workers)

    worker = input("Enter worker name: ")

    if worker not in workers:
        print("Invalid worker name!")
        conn.close()
        return

    start = input("Enter week start date (Sunday) YYYY-MM-DD: ")
    end = input("Enter week end date (Saturday) YYYY-MM-DD: ")

    cursor.execute("""
    SELECT d.date, d.output_quantity, l.rate_per_unit,
           d.output_quantity * l.rate_per_unit
    FROM daily_output d
    JOIN looms l ON d.loom_number = l.loom_number
    WHERE d.worker_name = ?
    AND d.date BETWEEN ? AND ?
    """, (worker, start, end))

    rows = cursor.fetchall()
    total = 0

    if not rows:
        print("No records found for this week.")
        conn.close()
        return

    print("\nDate | Output | Rate | Daily Pay")
    print("----------------------------------")

    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
        total += r[3]

    print("----------------------------------")
    print(f"Total Weekly Salary for {worker}: ₹{total}")

    conn.close()


# MAIN MENU
while True:
    print("\n=== POWERLOOM SALARY MANAGEMENT ===")
    print("1. Add Worker")
    print("2. Add Loom")
    print("3. Enter Daily Output")
    print("4. Calculate Weekly Salary")
    print("5. Exit")

    choice = input("Enter your choice (1-5): ")

    if choice == "1":
        add_worker()
    elif choice == "2":
        add_loom()
    elif choice == "3":
        daily_entry()
    elif choice == "4":
        weekly_salary()
    elif choice == "5":
        print("Exiting system...")
        break
    else:
        print("Invalid choice. Try again.")
