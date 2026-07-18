import sqlite3

# connect to database (creates file if not exists)
conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# create workers table
cursor.execute("""
CREATE TABLE IF NOT EXISTS workers (
    worker_name TEXT PRIMARY KEY,
    phone TEXT,
    active_status TEXT
)
""")

# create looms table
cursor.execute("""
CREATE TABLE IF NOT EXISTS looms (
    loom_number INTEGER PRIMARY KEY,
    rate_per_unit REAL,
    status TEXT DEFAULT 'Active',
    expected_daily_production INTEGER DEFAULT 100
)
""")

# create daily output table
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_output (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    worker_name TEXT,
    loom_number INTEGER,
    shift TEXT,
    output_quantity INTEGER,
    run_time_hours REAL DEFAULT 12.0,
    FOREIGN KEY (worker_name) REFERENCES workers (worker_name) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (loom_number) REFERENCES looms (loom_number) ON UPDATE CASCADE ON DELETE RESTRICT
)
""")

# create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    role TEXT
)
""")

# create loans table
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

# create loan_repayments table
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


# create incentive_targets table
cursor.execute("""
CREATE TABLE IF NOT EXISTS incentive_targets (
    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_quantity INTEGER NOT NULL UNIQUE,
    bonus_amount REAL NOT NULL,
    target_type TEXT DEFAULT 'Weekly'
)
""")

# Seed default target levels
cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (400, 200.0)")
cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (600, 500.0)")
cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (800, 1000.0)")


# Seed default admin and supervisor using werkzeug security hashing
from werkzeug.security import generate_password_hash

admin_pwd_hash = generate_password_hash("jotheeskavi")
supervisor_pwd_hash = generate_password_hash("supervisorpass")

cursor.execute(
    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
    ("jkt_textiles", admin_pwd_hash, "Admin")
)

cursor.execute(
    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
    ("jkt_supervisor", supervisor_pwd_hash, "Supervisor")
)

conn.commit()
conn.close()

print("Database and tables created successfully, users seeded")
