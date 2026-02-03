"""
Scrape top active PGA players for 2025 using combined API approach
1. Get top 50 player IDs from statistics leaders API
2. Fetch full 52 stats for each using individual player API
"""

import sys
sys.path.insert(0, 'data')

from espn_full_stats_scraper import ESPNFullStatsScraper
import requests
import time


def get_top_player_ids(year=2026):
    """Get player IDs from statistics leaders API"""

    url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics"
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"Fetching top players from {year} statistics API...")

    try:
        response = requests.get(url, params={'season': year}, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        categories = data.get('stats', {}).get('categories', [])

        # Collect unique player IDs from all categories
        player_ids = set()

        for category in categories:
            leaders = category.get('leaders', [])
            for leader in leaders:
                athlete = leader.get('athlete', {})
                player_id = athlete.get('id')
                if player_id:
                    player_ids.add(str(player_id))

        print(f"  Found {len(player_ids)} unique active players")
        return list(player_ids)

    except Exception as e:
        print(f"  Error: {e}")
        return []


def main():
    print("\n" + "="*80)
    print("SCRAPING TOP 2025 PGA PLAYERS - FULL STATS")
    print("="*80)

    # Get top player IDs from statistics API
    player_ids = get_top_player_ids(year=2026)

    if not player_ids:
        print("No players found!")
        return

    print(f"\nFetching full stats for {len(player_ids)} top players...")
    print("(This will take about 1-2 minutes)")

    scraper = ESPNFullStatsScraper()

    # Fetch stats for each player
    all_player_stats = []
    successful = 0
    failed = 0

    for i, player_id in enumerate(player_ids):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(player_ids)} players ({successful} successful)")

        stats = scraper.fetch_player_stats(player_id, year=2026)

        if stats:
            all_player_stats.append(stats)
            successful += 1
        else:
            failed += 1

        time.sleep(0.1)  # Be respectful

    print(f"\nCompleted: {successful} players with data, {failed} failed")

    # Save to database
    if all_player_stats:
        scraper.save_to_database(all_player_stats)

        # Verify with sample query
        print("\n" + "="*80)
        print("VERIFICATION - Top Players in Database:")
        print("="*80)

        import sqlite3
        import pandas as pd

        conn = sqlite3.connect('data/cache/pga_data.db')

        # Show players with their scoring average
        df = pd.read_sql("""
            SELECT DISTINCT p.player_name, s.stat_display_value as scoring_avg, s.rank
            FROM player_season_stats p
            JOIN player_season_stats s ON p.player_id = s.player_id AND p.year = s.year
            WHERE s.stat_name = 'scoringAverage' AND s.year = 2026
            ORDER BY s.rank
            LIMIT 20
        """, conn)

        print(df.to_string(index=False))

        conn.close()
    else:
        print("\nNo data to save!")


if __name__ == "__main__":
    main()
