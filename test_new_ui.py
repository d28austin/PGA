"""
Test the new UI queries
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

# Test tournament selector query
print("=" * 80)
print("TOURNAMENTS WITH DATA (for sidebar selector)")
print("=" * 80)

query = """
    SELECT
        tournament_id,
        tournament_id as tournament_name,
        year,
        COUNT(*) as player_count
    FROM tournament_results
    WHERE CAST(position AS INTEGER) > 0
    GROUP BY tournament_id, year
    ORDER BY year DESC, tournament_id
"""
df = pd.read_sql(query, conn)

if not df.empty:
    print(f"\nFound {len(df)} tournaments with data:\n")
    for _, row in df.iterrows():
        print(f"  • {row['tournament_name']} ({row['year']}) - {row['player_count']} players")
else:
    print("\nNo tournaments with data found.")

# Test year availability query for a specific tournament
print("\n" + "=" * 80)
print("YEARS AVAILABLE FOR FIRST TOURNAMENT")
print("=" * 80)

if not df.empty:
    first_tournament_id = df.iloc[0]['tournament_id']
    print(f"\nTournament ID: {first_tournament_id}")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT year
        FROM tournament_results
        WHERE tournament_id = ? AND CAST(position AS INTEGER) > 0
        ORDER BY year DESC
    """, (first_tournament_id,))
    available_years = [row[0] for row in cursor.fetchall()]

    print(f"Available years: {', '.join(map(str, available_years))}")

conn.close()

print("\n" + "=" * 80)
print("Test complete - UI queries working!")
print("=" * 80)
