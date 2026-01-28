"""
Debug Chris Kirk's score calculation
"""

import sqlite3
import pandas as pd
from data.database import PGADatabase

db = PGADatabase()

# Get The Sentry data
tournament_id = '401580329'
year = 2024

# Get par info
par_info = db.get_tournament_par(tournament_id, year)
print("=" * 80)
print("THE SENTRY PAR INFO")
print("=" * 80)
print(f"Par info: {par_info}")

if par_info:
    tournament_par = par_info['total_par']
    print(f"Tournament par: {tournament_par}")
else:
    print("ERROR: No par data found!")
    exit(1)

# Get Chris Kirk's scores
conn = sqlite3.connect('data/cache/pga_data.db')

query = """
    SELECT player_name, year, position, total_score
    FROM tournament_results
    WHERE tournament_id = ? AND player_name LIKE '%Kirk%'
    ORDER BY year, position
"""

df = pd.read_sql(query, conn, params=(tournament_id,))
conn.close()

print("\n" + "=" * 80)
print("CHRIS KIRK'S SCORES AT THE SENTRY")
print("=" * 80)

for _, row in df.iterrows():
    score = row['total_score']
    if pd.notna(score):
        score_to_par = score - tournament_par
        print(f"\nYear: {row['year']}")
        print(f"  Player: {row['player_name']}")
        print(f"  Position: {row['position']}")
        print(f"  Total Score: {score}")
        print(f"  Par: {tournament_par}")
        print(f"  Score to Par: {score_to_par:+d}")

print("\n" + "=" * 80)

# Check if there are multiple years
if len(df) > 1:
    print(f"\nWARNING: Chris Kirk has {len(df)} entries at The Sentry")
    print("The average might be calculated across multiple years")

    # Calculate average
    df['score_numeric'] = pd.to_numeric(df['total_score'], errors='coerce')
    df['score_to_par'] = df['score_numeric'] - tournament_par
    avg_score_to_par = df['score_to_par'].mean()
    print(f"\nAverage score to par: {avg_score_to_par:.1f}")
    print(f"Formatted: {avg_score_to_par:.0f}")
