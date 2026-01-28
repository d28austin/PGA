"""
Ensure database schema is up to date before starting the app
Run this before streamlit run app.py
"""

import sqlite3
import os

db_path = 'data/cache/pga_data.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    print("Run load_historical_data.py first to create the database")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("ENSURING DATABASE SCHEMA IS UP TO DATE")
print("=" * 80)

# Check current columns
cursor.execute("PRAGMA table_info(tournaments)")
existing_columns = [row[1] for row in cursor.fetchall()]

print(f"\nCurrent columns in tournaments table:")
print(f"  {', '.join(existing_columns)}")

# Add par columns if missing
par_columns = [
    ('par_per_round', 'INTEGER'),
    ('total_par', 'INTEGER'),
    ('rounds', 'INTEGER'),
    ('num_courses', 'INTEGER')
]

added = []
for col_name, col_type in par_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE tournaments ADD COLUMN {col_name} {col_type}")
            conn.commit()
            added.append(col_name)
            print(f"\n  Added column: {col_name}")
        except Exception as e:
            print(f"\n  Error adding {col_name}: {e}")

if added:
    print(f"\n{len(added)} column(s) added")
else:
    print("\nAll par columns already exist")

# Verify final schema
cursor.execute("PRAGMA table_info(tournaments)")
final_columns = [row[1] for row in cursor.fetchall()]

print(f"\nFinal columns:")
print(f"  {', '.join(final_columns)}")

# Check if par data exists
cursor.execute("SELECT COUNT(*) FROM tournaments WHERE par_per_round IS NOT NULL")
count = cursor.fetchone()[0]

print(f"\nTournaments with par data: {count}")

if count == 0:
    print("\nWARNING: No par data found. Run fetch_and_store_par_data.py to populate par data.")

conn.close()

print("\n" + "=" * 80)
print("DATABASE SCHEMA CHECK COMPLETE")
print("=" * 80)
