"""
Update earnings data for all tournaments in the database
"""

import sqlite3
import time
from scrape_espn_earnings import scrape_tournament_earnings

def update_all_earnings():
    """Update earnings for all tournaments in database"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Get all unique tournament_id and year combinations
    cursor.execute("""
        SELECT DISTINCT tournament_id, year
        FROM tournament_results
        ORDER BY year DESC, tournament_id
    """)

    tournaments = cursor.fetchall()

    print("=" * 80)
    print(f"UPDATING EARNINGS FOR {len(tournaments)} TOURNAMENTS")
    print("=" * 80)

    success_count = 0
    fail_count = 0
    total_players_updated = 0

    for i, (tournament_id, year) in enumerate(tournaments, 1):
        print(f"\n[{i}/{len(tournaments)}] {tournament_id} ({year})...", end='', flush=True)

        # Scrape earnings from ESPN
        earnings_data = scrape_tournament_earnings(tournament_id)

        if not earnings_data:
            print(" No earnings data")
            fail_count += 1
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

        print(f" OK ({len(earnings_data)} earnings, {players_updated} players updated)")
        success_count += 1
        total_players_updated += players_updated

        # Rate limiting - be nice to ESPN
        if i < len(tournaments):
            time.sleep(2)

    conn.close()

    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print(f"  Tournaments with earnings: {success_count}")
    print(f"  Tournaments without earnings: {fail_count}")
    print(f"  Total player records updated: {total_players_updated}")

if __name__ == "__main__":
    try:
        update_all_earnings()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
