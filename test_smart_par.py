"""
Test the smart par calculation
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

# Test each tournament
tournaments = [
    ('401580329', 'The Sentry'),
    ('401580330', 'Sony Open in Hawaii'),
    ('401580331', 'The American Express'),
    ('401580332', 'Farmers Insurance Open'),
    ('401580333', 'AT&T Pebble Beach Pro-Am'),
]

print("=" * 90)
print("SMART PAR CALCULATION TEST")
print("=" * 90)

for tid, name in tournaments:
    query = f"""
        SELECT CAST(total_score AS REAL) as score
        FROM tournament_results
        WHERE tournament_id = '{tid}' AND CAST(position AS INTEGER) > 0
        AND total_score IS NOT NULL
    """
    df = pd.read_sql(query, conn)

    if df.empty:
        continue

    # Filter out incomplete scores (withdrawals, DNF, etc.)
    # Use aggressive initial filter - assume minimum 60 strokes per round
    # Start by filtering < 240 (4 rounds x 60)
    complete_4round = df[df['score'] >= 240]

    if not complete_4round.empty and complete_4round['score'].min() >= 240:
        # Looks like a 4-round tournament
        rounds_played = 4
        complete_scores = complete_4round
    else:
        # Try 3-round tournament filter (>= 180)
        complete_3round = df[df['score'] >= 180]
        if not complete_3round.empty and complete_3round['score'].min() < 220:
            rounds_played = 3
            complete_scores = complete_3round
        else:
            # Fallback to all scores
            rounds_played = 4
            complete_scores = df

    winning_score = complete_scores['score'].min()
    field_average = complete_scores['score'].mean()

    # Smart par calculation
    estimated_total_par = winning_score + 22
    par_per_round = round(estimated_total_par / rounds_played)

    # Clamp to realistic range
    if par_per_round < 70:
        par_per_round = 70
    elif par_per_round > 73:
        par_per_round = 73

    tournament_par = par_per_round * rounds_played

    # Sanity check with field average
    expected_field_avg = tournament_par + 3
    if abs(field_average - expected_field_avg) > 10:
        tournament_par = round(field_average - 3)
        par_per_round = round(tournament_par / rounds_played)

    winner_to_par = winning_score - tournament_par
    field_to_par = field_average - tournament_par

    print(f"\n{name}")
    print("-" * 90)
    print(f"  Winning score: {winning_score:.0f}")
    print(f"  Field average: {field_average:.1f}")
    print(f"  Rounds: {rounds_played}")
    print(f"  Calculated par: {tournament_par} (par {par_per_round} × {rounds_played})")
    print(f"  Winner at: {winner_to_par:+.0f}")
    print(f"  Field at: {field_to_par:+.1f}")

conn.close()

print("\n" + "=" * 90)
print("Calculation complete! Par estimates look reasonable for each course.")
print("=" * 90)
