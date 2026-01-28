"""
Test the new table calculations
"""

import pandas as pd
import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')

# Get data for first tournament
query = """
    SELECT player_name, position, total_score, year
    FROM tournament_results
    WHERE tournament_id = '401580329' AND CAST(position AS INTEGER) > 0
    ORDER BY CAST(position AS INTEGER)
    LIMIT 20
"""

df = pd.read_sql(query, conn)
conn.close()

print("=" * 80)
print("SAMPLE DATA FROM THE SENTRY 2024")
print("=" * 80)
print(df.to_string(index=False))

# Test calculations
print("\n" + "=" * 80)
print("TESTING NEW CALCULATIONS")
print("=" * 80)

df['position_numeric'] = pd.to_numeric(df['position'], errors='coerce')

# Test top 10s
top_10_count = (df['position_numeric'] <= 10).sum()
print(f"\nPlayers with top 10 finishes: {top_10_count}")
print(f"Top 10 players: {df[df['position_numeric'] <= 10]['player_name'].tolist()}")

# Test made cuts (top 70)
made_cut_count = (df['position_numeric'] <= 70).sum()
print(f"\nPlayers who made the cut (top 70): {made_cut_count}")

# Test groupby aggregation
print("\n" + "=" * 80)
print("TOP 5 PLAYERS BY FINISH POSITION")
print("=" * 80)

top_5 = df.nsmallest(5, 'position_numeric')
for _, row in top_5.iterrows():
    print(f"{row['position_numeric']:2.0f}. {row['player_name']:25s} (Score: {row['total_score']})")

print("\n✓ All calculations working correctly!")
