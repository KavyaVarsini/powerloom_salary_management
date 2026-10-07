import sqlite3
import random
from datetime import datetime, timedelta

def populate_database():
    conn = sqlite3.connect("powerloom.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. 60 Tamil Workers List
    tamil_workers = [
        "Arumugam", "Subramaniam", "Muthusamy", "Chinnasamy", "Periyasamy",
        "Ramasamy", "Palanisamy", "Velayutham", "Kandasamy", "Govindasamy",
        "Karuppasamy", "Muthuvel", "Shanmugam", "Thangavel", "Marimuthu",
        "Chidambaram", "Natarajan", "Krishnasamy", "Doraisamy", "Veerasamy",
        "Rathinam", "Ponnusamy", "Madasamy", "Munusamy", "Alagappan",
        "Sellappan", "Duraisamy", "Manickam", "Ranganathan", "Thirumalai",
        "Alamelu", "Meenakshi", "Kamatchi", "Ponnammal", "Chinnammal",
        "Periyammal", "Muthulakshmi", "Rajammal", "Lakshmi", "Parvathi",
        "Saraswathi", "Valli", "Deivanai", "Angammal", "Dhanalakshmi",
        "Thangammal", "Pappammal", "Kannammal", "Maragatham", "Sivakami",
        "Bhagyammal", "Gomathi", "Visalakshi", "Soundarammal", "Chellammal",
        "Muniyammal", "Kuppammal", "Azhagammal", "Veerammal", "Ponnuthayi"
    ]

    print(f"Adding/Updating {len(tamil_workers)} Tamil workers into database...")
    for idx, worker_name in enumerate(tamil_workers, start=1):
        phone = f"987654{idx:04d}"
        cursor.execute("""
            INSERT OR REPLACE INTO workers (worker_name, phone, active_status)
            VALUES (?, ?, 'Active')
        """, (worker_name, phone))

    # 2. Fetch Active Looms
    cursor.execute("SELECT loom_number FROM looms WHERE status='Active'")
    active_looms = [row[0] for row in cursor.fetchall()]
    if not active_looms:
        # Fallback if no active looms exist
        active_looms = list(range(1, 61))
        for l in active_looms:
            cursor.execute("INSERT OR IGNORE INTO looms (loom_number, rate_per_unit, status) VALUES (?, 5.5, 'Active')", (l,))

    # 3. Clean up old July-October mock records if any, to avoid duplicate key conflicts or inconsistent historical state
    cursor.execute("DELETE FROM daily_output WHERE date BETWEEN '2026-07-01' AND '2026-10-31'")

    # 4. Generate daily entries from July 1, 2026 to October 31, 2026
    start_date = datetime(2026, 7, 1)
    end_date = datetime(2026, 10, 31)
    
    current_date = start_date
    shifts = ["Morning", "Night"]
    
    total_records = 0
    records_to_insert = []

    print(f"Generating daily output entries from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

    # Set random seed for reproducible realistic dataset
    random.seed(42)

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Each day, assign workers across shifts and looms
        # Select 40-50 workers active on this day
        daily_workers = random.sample(tamil_workers, k=random.randint(45, 55))
        
        loom_pool = active_looms.copy()
        random.shuffle(loom_pool)
        loom_idx = 0

        for worker in daily_workers:
            # Assign shift
            shift = random.choice(shifts)
            loom = loom_pool[loom_idx % len(loom_pool)]
            loom_idx += 1
            
            # Output quantity with realistic distribution (mostly 110-170 units)
            # Occasional lower (80-100) or higher (170-195) output
            output_quantity = int(random.gauss(135, 18))
            output_quantity = max(75, min(200, output_quantity))
            
            run_time = 12.0 if random.random() > 0.05 else round(random.uniform(8.0, 11.5), 1)

            records_to_insert.append((date_str, worker, loom, shift, output_quantity, run_time))
            total_records += 1

        current_date += timedelta(days=1)

    # Executemany for maximum efficiency
    cursor.executemany("""
        INSERT INTO daily_output (date, worker_name, loom_number, shift, output_quantity, run_time_hours)
        VALUES (?, ?, ?, ?, ?, ?)
    """, records_to_insert)

    # 5. Add sample loans and repayments for Tamil workers for comprehensive testing
    sample_loan_workers = ["Arumugam", "Muthusamy", "Karuppasamy", "Shanmugam", "Alamelu", "Meenakshi", "Gomathi"]
    for idx, wname in enumerate(sample_loan_workers, 1):
        # Check if loan already exists for worker
        cursor.execute("SELECT COUNT(*) FROM loans WHERE worker_name=?", (wname,))
        if cursor.fetchone()[0] == 0:
            loan_amount = 3000.0 + (idx * 1000.0)
            loan_date = f"2026-07-{(idx * 3):02d}"
            cursor.execute("""
                INSERT INTO loans (worker_name, amount, date_given, description, repaid_amount, status)
                VALUES (?, ?, ?, 'Festival Advance', ?, 'Active')
            """, (wname, loan_amount, loan_date, 500.0))
            loan_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO loan_repayments (loan_id, worker_name, amount, repayment_date, repayment_type, notes)
                VALUES (?, ?, 500.0, ?, 'Direct Cash', 'Advance repayment')
            """, (loan_id, wname, loan_date))

    conn.commit()
    conn.close()
    print(f"Successfully added {len(tamil_workers)} Tamil workers and generated {total_records} daily output records from July to October!")

if __name__ == "__main__":
    populate_database()
