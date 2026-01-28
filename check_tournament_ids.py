"""
Check what tournament IDs are in the tournaments table
"""

import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

cursor.execute("SELECT tournament_id, year, par_per_round, total_par, rounds FROM tournaments LIMIT 20")
rows = cursor.fetchall()

print("=" * 80)
print(f"TOURNAMENTS TABLE - Found {len(rows)} rows")
print("=" * 80)

for row in rows:
    print(f"ID: {row[0]}, Year: {row[1]}, Par/Round: {row[2]}, Total: {row[3]}, Rounds: {row[4]}")

# Also check what tournament_ids exist in tournament_results
print("\n" + "=" * 80)
print("TOURNAMENT IDs IN TOURNAMENT_RESULTS")
print("=" * 80)

cursor.execute("SELECT DISTINCT tournament_id FROM tournament_results")
result_ids = cursor.fetchall()

for row in result_ids:
    print(f"  {row[0]}")

conn.close()
