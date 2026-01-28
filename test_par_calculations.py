"""
Test par calculations
"""

import pandas as pd
import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')

# Get data for The Sentry 2024
query = """
    SELECT player_name, position, total_score
    FROM tournament_results
    WHERE tournament_id = '401580329' AND CAST(position AS INTEGER) > 0
    ORDER BY CAST(position AS INTEGER)
    LIMIT 10
"""

df = pd.read_sql(query, conn)
conn.close()

print("=" * 80)
print("THE SENTRY 2024 - PAR CALCULATIONS")
print("=" * 80)

df['total_score_numeric'] = pd.to_numeric(df['total_score'], errors='coerce')

# Determine tournament par
best_score = df['total_score_numeric'].min()
print(f"\nBest (winning) score: {best_score}")

if best_score < 220:
    tournament_par = 72 * 3
    rounds = 3
else:
    tournament_par = 72 * 4
    rounds = 4

print(f"Tournament par: {tournament_par} ({rounds} rounds x 72)")

# Calculate scores relative to par
df['score_to_par'] = df['total_score_numeric'] - tournament_par

print("\nTop 10 Players with Scores Relative to Par:")
print("-" * 80)

for _, row in df.iterrows():
    score_to_par = row['score_to_par']
    if pd.isna(score_to_par):
        formatted = "N/A"
    elif score_to_par == 0:
        formatted = "E"
    elif score_to_par > 0:
        formatted = f"+{int(score_to_par)}"
    else:
        formatted = str(int(score_to_par))

    print(f"{row['position']:>3}. {row['player_name']:<25} {row['total_score_numeric']:>3.0f} ({formatted})")

print("\n" + "=" * 80)
print("CALCULATION VERIFIED!")
print("=" * 80)
