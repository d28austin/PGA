"""
Fetch and store par data for all tournaments in the database
"""

import sqlite3
from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase

# Initialize
fetcher = ESPNPGAFetcher()
db = PGADatabase()

# Get all unique tournament_id and year combinations from the database
conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT tournament_id, year
    FROM tournament_results
    ORDER BY year DESC, tournament_id
""")

tournaments = cursor.fetchall()

print("=" * 80)
print(f"FETCHING PAR DATA FOR {len(tournaments)} TOURNAMENTS")
print("=" * 80)

success_count = 0
fail_count = 0

for tournament_id, year in tournaments:
    try:
        print(f"\n{tournament_id} ({year})... ", end="")

        # Get par data from API
        par_data = fetcher.get_tournament_par(tournament_id)

        if par_data:
            # Determine rounds from actual scores in database
            # Use aggressive filter to exclude incomplete scores
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
                # Valid 4-round scores found
                rounds = 4
            else:
                # Check for 3-round tournament
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

                if min_score_3round:
                    rounds = 3
                else:
                    rounds = 4  # Default to 4

            # Add rounds to par_data
            par_data['rounds'] = rounds
            par_data['total_par'] = par_data['par_per_round'] * rounds

            # Save to database
            db.save_tournament_par(tournament_id, year, par_data)
            print(f"OK - Par {par_data['par_per_round']} x {rounds} = {par_data['total_par']}")
            success_count += 1
        else:
            print(f"FAIL - No par data available")
            fail_count += 1

    except Exception as e:
        print(f"ERROR: {e}")
        fail_count += 1

conn.close()

print("\n" + "=" * 80)
print(f"COMPLETE: {success_count} successful, {fail_count} failed")
print("=" * 80)
