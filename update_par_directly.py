"""
Directly update par data in tournaments table
"""

import sqlite3
from data.espn_fetcher import ESPNPGAFetcher

fetcher = ESPNPGAFetcher()
conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

# Get tournament IDs from tournament_results
cursor.execute("SELECT DISTINCT tournament_id, year FROM tournament_results WHERE tournament_id != 'T001' ORDER BY year DESC, tournament_id")
tournaments = cursor.fetchall()

print("=" * 80)
print(f"UPDATING PAR DATA FOR {len(tournaments)} TOURNAMENTS")
print("=" * 80)

success_count = 0

for tournament_id, year in tournaments:
    print(f"\n{tournament_id} ({year})... ", end="")

    # Get par data from ESPN
    par_data = fetcher.get_tournament_par(tournament_id)

    if not par_data:
        print("FAIL - No par data from ESPN")
        continue

    # Determine rounds from actual scores
    cursor.execute("""
        SELECT MIN(CAST(total_score AS REAL))
        FROM tournament_results
        WHERE tournament_id = ? AND year = ?
        AND total_score IS NOT NULL
        AND CAST(total_score AS REAL) >= 240
    """, (tournament_id, year))

    result_4round = cursor.fetchone()
    min_score_4round = result_4round[0] if result_4round and result_4round[0] else None

    if min_score_4round:
        rounds = 4
    else:
        cursor.execute("""
            SELECT MIN(CAST(total_score AS REAL))
            FROM tournament_results
            WHERE tournament_id = ? AND year = ?
            AND total_score IS NOT NULL
            AND CAST(total_score AS REAL) >= 180
            AND CAST(total_score AS REAL) < 240
        """, (tournament_id, year))

        result_3round = cursor.fetchone()
        min_score_3round = result_3round[0] if result_3round and result_3round[0] else None

        rounds = 3 if min_score_3round else 4

    par_per_round = par_data['par_per_round']
    total_par = par_per_round * rounds
    num_courses = par_data['num_courses']

    # Insert or update - use composite key with year
    composite_id = f"{tournament_id}_{year}"
    cursor.execute("""
        INSERT OR REPLACE INTO tournaments
        (tournament_id, tournament_name, year, par_per_round, total_par, rounds, num_courses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (composite_id, f"Tournament {tournament_id}", year, par_per_round, total_par, rounds, num_courses))

    conn.commit()
    print(f"OK - Par {par_per_round} x {rounds} = {total_par}")
    success_count += 1

conn.close()

print("\n" + "=" * 80)
print(f"COMPLETE: {success_count} tournaments updated")
print("=" * 80)
