import sqlite3

def run_migration():
    conn = sqlite3.connect("powerloom.db")
    cursor = conn.cursor()

    # Create incentive_targets table
    print("Creating incentive_targets table if not exists...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incentive_targets (
        target_id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_quantity INTEGER NOT NULL UNIQUE,
        bonus_amount REAL NOT NULL,
        target_type TEXT DEFAULT 'Weekly'
    )
    """)

    # Seed default target levels (if not already seeded)
    print("Seeding initial target tiers...")
    cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (400, 200.0)")
    cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (600, 500.0)")
    cursor.execute("INSERT OR IGNORE INTO incentive_targets (target_quantity, bonus_amount) VALUES (800, 1000.0)")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
