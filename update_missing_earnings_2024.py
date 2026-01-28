"""
Update earnings for 2024 tournaments that are missing earnings data
Targets the 12 tournaments with NO earnings and 30 with PARTIAL earnings
"""

import sqlite3
import time
from scrape_espn_earnings import scrape_tournament_earnings

def update_missing_earnings():
    """Update earnings for tournaments missing data"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Get tournaments with missing or partial earnings
    cursor.execute('''
        SELECT
            tournament_id,
            tournament_name,
            COUNT(*) as total_players,
            SUM(CASE WHEN earnings IS NOT NULL AND earnings > 0 THEN 1 ELSE 0 END) as players_with_earnings
        FROM tournament_results
        WHERE year = 2024
        AND tournament_id != 'T001'
        GROUP BY tournament_id, tournament_name
        HAVING players_with_earnings < total_players * 0.9
        ORDER BY players_with_earnings
    ''')

    tournaments = cursor.fetchall()

    print('=' * 80)
    print(f'UPDATING EARNINGS FOR {len(tournaments)} TOURNAMENTS WITH MISSING DATA')
    print('=' * 80)
    print()

    success_count = 0
    fail_count = 0
    total_players_updated = 0

    for i, (tournament_id, tournament_name, total_players, players_with_earnings) in enumerate(tournaments, 1):
        coverage_pct = (players_with_earnings / total_players * 100) if total_players > 0 else 0

        print(f'\n[{i}/{len(tournaments)}] {tournament_name}')
        print(f'  Tournament ID: {tournament_id}')
        print(f'  Current coverage: {players_with_earnings}/{total_players} ({coverage_pct:.0f}%)')
        print(f'  Scraping earnings...', end='', flush=True)

        # Scrape earnings from ESPN
        earnings_data = scrape_tournament_earnings(tournament_id)

        if not earnings_data:
            print(' No earnings found on ESPN')
            fail_count += 1
            time.sleep(1)
            continue

        # Update database
        players_updated = 0
        for player_name, earnings in earnings_data.items():
            cursor.execute("""
                UPDATE tournament_results
                SET earnings = ?
                WHERE tournament_id = ? AND year = 2024 AND player_name = ?
            """, (earnings, tournament_id, player_name))

            if cursor.rowcount > 0:
                players_updated += cursor.rowcount

        conn.commit()

        print(f' OK')
        print(f'  Scraped: {len(earnings_data)} earnings')
        print(f'  Updated: {players_updated} records')
        success_count += 1
        total_players_updated += players_updated

        # Rate limiting
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
    print('Run check_missing_earnings.py again to verify coverage improved.')

if __name__ == "__main__":
    try:
        update_missing_earnings()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
