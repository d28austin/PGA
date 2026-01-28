"""
Smart par calculation based on score distribution
"""

import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('data/cache/pga_data.db')

# Get all tournaments
query = """
SELECT tournament_id, year, COUNT(*) as player_count,
       MIN(CAST(total_score AS REAL)) as winning_score,
       AVG(CAST(total_score AS REAL)) as avg_score,
       MAX(CAST(total_score AS REAL)) as worst_score
FROM tournament_results
WHERE CAST(position AS INTEGER) > 0 AND total_score IS NOT NULL
GROUP BY tournament_id, year
"""

tournaments = pd.read_sql(query, conn)
conn.close()

print("=" * 80)
print("ANALYZING TOURNAMENT SCORES TO ESTIMATE PAR")
print("=" * 80)

for _, tourn in tournaments.iterrows():
    tid = tourn['tournament_id']
    year = tourn['year']
    win_score = tourn['winning_score']
    avg_score = tourn['avg_score']

    # Estimate rounds based on score range
    if win_score < 220:
        rounds = 3
    else:
        rounds = 4

    # Method 1: Assume winner is typically -15 to -25
    # So par = winning_score + 20 (middle estimate)
    estimated_par_1 = win_score + 20

    # Method 2: Assume field average is around +2 to +4 over par
    # So par = avg_score - 3
    estimated_par_2 = avg_score - 3

    # Method 3: Standard par based on rounds
    standard_par = rounds * 72

    print(f"\nTournament: {tid} ({year})")
    print(f"  Winning score: {win_score}")
    print(f"  Field average: {avg_score:.1f}")
    print(f"  Estimated rounds: {rounds}")
    print(f"  Estimated par (winner method): {estimated_par_1:.0f}")
    print(f"  Estimated par (field method): {estimated_par_2:.0f}")
    print(f"  Standard par ({rounds} x 72): {standard_par}")

    # Best guess: Use winning score + 20-25 as par estimate
    # Then round to nearest multiple of rounds
    estimated_par = round((win_score + 22) / rounds) * rounds
    print(f"  BEST ESTIMATE: {estimated_par} (par {estimated_par/rounds:.0f} per round)")

    # Sanity check
    winner_to_par = win_score - estimated_par
    print(f"  Winner would be: {winner_to_par:+.0f}")

print("\n" + "=" * 80)
print("RECOMMENDATION: Use dynamic par calculation or maintain par lookup table")
print("=" * 80)
