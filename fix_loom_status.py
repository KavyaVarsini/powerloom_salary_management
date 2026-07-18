import sqlite3

conn = sqlite3.connect("powerloom.db")
cursor = conn.cursor()

# Set Active for any loom where status is NULL or empty
cursor.execute("""
UPDATE looms
SET status = 'Active'
WHERE status IS NULL OR status = ''
""")

conn.commit()
conn.close()

print("All NULL loom statuses fixed to Active")
