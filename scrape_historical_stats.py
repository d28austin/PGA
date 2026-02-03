"""
Scrape historical stats (2014-2026) for all current players in database
This provides comprehensive data for regression modeling
"""

import sys
sys.path.insert(0, 'data')

from espn_full_stats_scraper import ESPNFullStatsScraper
import sqlite3
import time


def get_current_player_ids(db_path="data/cache/pga_data.db"):
    """Get all unique player IDs currently in database"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT player_id, player_name
        FROM player_season_stats
        WHERE player_id IS NOT NULL
        ORDER BY player_name
    """)

    players = cursor.fetchall()
    conn.close()

    print(f"Found {len(players)} unique players in database")
    print("\nSample players:")
    for player_id, name in players[:10]:
        print(f"  {name} (ID: {player_id})")

    return [(pid, name) for pid, name in players]


def main():
    print("\n" + "="*80)
    print("HISTORICAL STATS SCRAPER (2014-2026)")
    print("="*80)
    print("\nFetching comprehensive historical data for all current players")
    print("This will provide 13 years of data for regression modeling")
    print()

    # Get current players
    players = get_current_player_ids()

    if not players:
        print("No players found in database!")
        return

    # Years to scrape (2014-2026)
    years = list(range(2014, 2027))  # 2014 through 2026

    print(f"\nPlayers to scrape: {len(players)}")
    print(f"Years to scrape: {len(years)} years ({years[0]}-{years[-1]})")
    print(f"Total API calls: ~{len(players) * len(years):,}")
    print(f"Estimated time: {len(players) * len(years) * 0.12 / 60:.1f} minutes")
    print("\nStarting in 3 seconds...")
    time.sleep(3)

    scraper = ESPNFullStatsScraper()

    # Track overall progress
    total_calls = len(players) * len(years)
    completed_calls = 0
    successful_seasons = 0
    failed_seasons = 0

    print("\n" + "="*80)
    print("STARTING HISTORICAL SCRAPE")
    print("="*80)

    # Process each year
    for year in years:
        print(f"\n{'='*80}")
        print(f"SCRAPING {year} SEASON")
        print(f"{'='*80}")

        year_player_stats = []
        year_successful = 0
        year_failed = 0

        for i, (player_id, player_name) in enumerate(players):
            # Progress indicator every 25 players
            if (i + 1) % 25 == 0:
                pct = (completed_calls / total_calls) * 100
                print(f"  Progress: {i+1}/{len(players)} players in {year} | Overall: {completed_calls}/{total_calls} ({pct:.1f}%)")

            stats = scraper.fetch_player_stats(player_id, year)

            if stats:
                year_player_stats.append(stats)
                year_successful += 1
                successful_seasons += 1
            else:
                year_failed += 1
                failed_seasons += 1

            completed_calls += 1

            # Be respectful to API
            time.sleep(0.1)

        print(f"\n{year} Summary:")
        print(f"  Players with data: {year_successful}")
        print(f"  No data: {year_failed}")

        # Save year's data to database
        if year_player_stats:
            print(f"  Saving {year} data to database...")
            scraper.save_to_database(year_player_stats)

        # Small delay between years
        time.sleep(1)

    # Final summary
    print("\n" + "="*80)
    print("HISTORICAL SCRAPE COMPLETE")
    print("="*80)
    print(f"Total API calls: {completed_calls:,}")
    print(f"Successful: {successful_seasons:,}")
    print(f"Failed/No data: {failed_seasons:,}")

    # Show database summary
    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(DISTINCT player_name) as players,
            COUNT(DISTINCT year) as years,
            COUNT(DISTINCT stat_name) as stats,
            COUNT(*) as total_records
        FROM player_season_stats
    """)

    summary = cursor.fetchone()
    players_count, years_count, stats_count, total_records = summary

    print(f"\n{'='*80}")
    print("FINAL DATABASE SUMMARY")
    print(f"{'='*80}")
    print(f"Total Players: {players_count:,}")
    print(f"Years of Data: {years_count}")
    print(f"Stat Types: {stats_count}")
    print(f"Total Records: {total_records:,}")

    # Show records per year
    cursor.execute("""
        SELECT year, COUNT(*) as records
        FROM player_season_stats
        GROUP BY year
        ORDER BY year DESC
    """)

    print(f"\nRecords by Year:")
    for year, count in cursor.fetchall():
        print(f"  {year}: {count:,} records")

    conn.close()

    print(f"\n{'='*80}")
    print("Ready for regression modeling!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
