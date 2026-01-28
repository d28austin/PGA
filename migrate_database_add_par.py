"""
Migration script to add par columns to the tournaments table
"""

import sqlite3

db_path = 'data/cache/pga_data.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("MIGRATING DATABASE: Adding par columns to tournaments table")
print("=" * 80)

# List of columns to add
columns_to_add = [
    ('par_per_round', 'INTEGER'),
    ('total_par', 'INTEGER'),
    ('rounds', 'INTEGER'),
    ('num_courses', 'INTEGER')
]

for column_name, column_type in columns_to_add:
    try:
        # Check if column exists
        cursor.execute(f"PRAGMA table_info(tournaments)")
        columns = [row[1] for row in cursor.fetchall()]

        if column_name not in columns:
            print(f"Adding column: {column_name} {column_type}... ", end="")
            cursor.execute(f"ALTER TABLE tournaments ADD COLUMN {column_name} {column_type}")
            print("OK")
        else:
            print(f"Column {column_name} already exists - OK")

    except Exception as e:
        print(f"ERROR adding {column_name}: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("MIGRATION COMPLETE")
print("=" * 80)
