"""
Update earnings for ALL tournaments (2020-2024) using the new API-based scraper
"""

import sqlite3
import time
from scrape_espn_earnings import scrape_tournament_earnings

def update_all_earnings():
    """Update earnings for all tournaments"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Get all tournaments from 2020-2024
    cursor.execute("""
        SELECT DISTINCT tournament_id, year, tournament_name
        FROM tournament_results
        WHERE year BETWEEN 2020 AND 2024
        ORDER BY year, tournament_id
    """)

    tournaments = cursor.fetchall()

    print('=' * 80)
    print(f'UPDATING EARNINGS FOR {len(tournaments)} TOURNAMENTS (2020-2024)')
    print('=' * 80)
    print()

    success_count = 0
    fail_count = 0
    total_players_updated = 0

    for i, (tournament_id, year, tournament_name) in enumerate(tournaments, 1):
        print(f'[{i}/{len(tournaments)}] {year} - {tournament_name[:40]}')
        print(f'  ID: {tournament_id}... ', end='', flush=True)

        # Scrape earnings from ESPN API
        earnings_data = scrape_tournament_earnings(tournament_id)

        if not earnings_data:
            print('No earnings')
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

        print(f'OK ({len(earnings_data)} earnings, {players_updated} updated)')
        success_count += 1
        total_players_updated += players_updated

        # Rate limiting - be nice to ESPN
        time.sleep(2)

    conn.close()

    print()
    print('=' * 80)
    print('UPDATE COMPLETE')
    print('=' * 80)
    print(f'  Tournaments processed: {len(tournaments)}')
    print(f'  Success: {success_count}')
    print(f'  Failed: {fail_count}')
    print(f'  Total player records updated: {total_players_updated}')
    print()
    print('Run check_missing_earnings.py to verify coverage improved.')

if __name__ == "__main__":
    try:
        update_all_earnings()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
