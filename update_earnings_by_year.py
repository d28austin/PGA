"""
Update earnings data for a specific year
"""

import sqlite3
import time
import sys
from scrape_espn_earnings import scrape_tournament_earnings

def update_earnings_for_year(year):
    """Update earnings for tournaments in a specific year"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Get tournaments for the specified year
    cursor.execute("""
        SELECT DISTINCT tournament_id, year
        FROM tournament_results
        WHERE year = ?
        ORDER BY tournament_id
    """, (year,))

    tournaments = cursor.fetchall()

    print("=" * 80)
    print(f"UPDATING EARNINGS FOR {len(tournaments)} {year} TOURNAMENTS")
    print("=" * 80)

    success_count = 0
    fail_count = 0
    total_players_updated = 0

    for i, (tournament_id, year) in enumerate(tournaments, 1):
        print(f"\n[{i}/{len(tournaments)}] {tournament_id}...", end='', flush=True)

        # Scrape earnings from ESPN
        earnings_data = scrape_tournament_earnings(tournament_id)

        if not earnings_data:
            print(" No earnings")
            fail_count += 1
            time.sleep(1)
            continue

        # Update database
        players_updated = 0
        for player_name, earnings in earnings_data.items():
            cursor.execute("""
                UPDATE tournament_results
                SET earnings = ?
                WHERE tournament_id = ? AND year = ? AND player_name = ?
            """, (earnings, tournament_id, year, player_name))

            if cursor.rowcount > 0:
                players_updated += cursor.rowcount

        conn.commit()

        print(f" OK ({len(earnings_data)} earnings, {players_updated} updated)")
        success_count += 1
        total_players_updated += players_updated

        # Rate limiting
        time.sleep(2)

    conn.close()

    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total players updated: {total_players_updated}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_earnings_by_year.py <year>")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
        update_earnings_for_year(year)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
