import sqlite3

# Connect to your database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='school_management_schedule'")
table_exists = cursor.fetchone()

if table_exists:
    print("✓ Table 'school_management_schedule' exists!")
    print("Checking columns...")
    cursor.execute("PRAGMA table_info(school_management_schedule)")
    columns = cursor.fetchall()
    print("\nColumns in the table:")
    for col in columns:
        print(f"  - {col[1]} (Type: {col[2]})")
else:
    print("✗ Table 'school_management_schedule' does NOT exist!")
    print("\nHere are all your tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        print(f"  - {table[0]}")

conn.close()