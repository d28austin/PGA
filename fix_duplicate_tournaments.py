"""
Fix duplicate tournament entries in the database
"""

import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

print("=" * 80)
print("CLEANING UP DUPLICATE TOURNAMENT ENTRIES")
print("=" * 80)

# Delete all tournament entries
cursor.execute("DELETE FROM tournaments")
print(f"\nDeleted all tournament entries")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("DONE - Now run fetch_and_store_par_data.py to repopulate")
print("=" * 80)
