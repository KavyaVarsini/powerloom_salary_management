import sqlite3

def run_migration():
    conn = sqlite3.connect("powerloom.db")
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create loans table
    print("Creating loans table if not exists...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_name TEXT NOT NULL,
        amount REAL NOT NULL,
        date_given TEXT NOT NULL,
        description TEXT,
        repaid_amount REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (worker_name) REFERENCES workers (worker_name) ON UPDATE CASCADE ON DELETE RESTRICT
    )
    """)

    # Create loan_repayments table
    print("Creating loan_repayments table if not exists...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loan_repayments (
        repayment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        worker_name TEXT NOT NULL,
        amount REAL NOT NULL,
        repayment_date TEXT NOT NULL,
        repayment_type TEXT NOT NULL, -- 'Salary Deduction', 'Direct Cash'
        salary_start_date TEXT,
        salary_end_date TEXT,
        notes TEXT,
        FOREIGN KEY (loan_id) REFERENCES loans (loan_id) ON DELETE CASCADE,
        FOREIGN KEY (worker_name) REFERENCES workers (worker_name) ON UPDATE CASCADE ON DELETE RESTRICT
    )
    """)

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
