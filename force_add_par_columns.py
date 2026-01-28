"""
Forcefully add par columns to tournaments table
"""

import sqlite3

db_path = 'data/cache/pga_data.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("ADDING PAR COLUMNS TO TOURNAMENTS TABLE")
print("=" * 80)

# Check current columns
cursor.execute("PRAGMA table_info(tournaments)")
current_cols = [row[1] for row in cursor.fetchall()]
print(f"\nCurrent columns: {', '.join(current_cols)}")

columns_to_add = [
    'par_per_round',
    'total_par',
    'rounds',
    'num_courses'
]

for col_name in columns_to_add:
    if col_name not in current_cols:
        try:
            sql = f"ALTER TABLE tournaments ADD COLUMN {col_name} INTEGER"
            print(f"\nExecuting: {sql}")
            cursor.execute(sql)
            print(f"  SUCCESS: Added {col_name}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print(f"\n{col_name} already exists")

conn.commit()

# Verify columns were added
cursor.execute("PRAGMA table_info(tournaments)")
final_cols = [row[1] for row in cursor.fetchall()]
print(f"\nFinal columns: {', '.join(final_cols)}")

conn.close()

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
