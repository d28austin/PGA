"""
Debug The American Express scores
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

# Get all scores for The American Express, ordered by score
query = """
    SELECT player_name, position, CAST(total_score AS REAL) as score
    FROM tournament_results
    WHERE tournament_id = '401580331'
    AND total_score IS NOT NULL
    ORDER BY score
"""

df = pd.read_sql(query, conn)
conn.close()

print("=" * 80)
print("THE AMERICAN EXPRESS - ALL SCORES")
print("=" * 80)
print(f"\nTotal scores found: {len(df)}")
print(f"Score range: {df['score'].min():.0f} to {df['score'].max():.0f}")
print(f"\nFirst 20 scores (lowest):")
print(df.head(20).to_string(index=False))

print(f"\n\nScores >= 180 and < 220:")
filtered = df[(df['score'] >= 180) & (df['score'] < 220)]
print(f"Count: {len(filtered)}")
print(filtered.to_string(index=False))

print(f"\n\nScores >= 240:")
filtered_240 = df[df['score'] >= 240]
print(f"Count: {len(filtered_240)}")
print(f"Min: {filtered_240['score'].min():.0f}")
print(f"Max: {filtered_240['score'].max():.0f}")
print(f"Mean: {filtered_240['score'].mean():.1f}")
print(filtered_240.head(10).to_string(index=False))
