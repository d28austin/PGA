"""
Load all historical PGA Tour data from 2020-2025
"""

import time
from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase

def load_all_data(start_year=2020, end_year=2025):
    """Load all tournament data for specified year range"""

    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    total_tournaments = 0
    total_players = 0

    print("=" * 100)
    print(f"LOADING ALL PGA TOUR DATA: {start_year}-{end_year}")
    print("=" * 100)
    print("\nThis will take several minutes due to API rate limiting...")
    print("Progress will be saved continuously, so you can stop and resume if needed.\n")

    for year in range(start_year, end_year + 1):
        print(f"\n{'=' * 100}")
        print(f"YEAR: {year}")
        print('=' * 100)

        # Get tournament calendar for the year
        print(f"\nFetching {year} calendar...")
        calendar = fetcher.get_season_calendar(year)

        if not calendar:
            print(f"No calendar data found for {year}")
            continue

        print(f"Found {len(calendar)} tournaments for {year}\n")

        year_tournaments = 0
        year_players = 0

        for i, tournament in enumerate(calendar, 1):
            event_id = tournament.get('event_id')
            name = tournament.get('name', 'Unknown Tournament')

            print(f"\n[{i}/{len(calendar)}] {name} ({event_id})")
            print("-" * 100)

            # Fetch tournament results
            results_df = fetcher.get_tournament_results(event_id, year)

            if results_df.empty:
                print("  No results available")
                continue

            # Save results
            db.save_tournament_results(results_df)

            player_count = len(results_df)
            year_players += player_count
            year_tournaments += 1

            print(f"  SUCCESS: Saved {player_count} player results")

            # Rate limiting - be respectful to ESPN's servers
            if i < len(calendar):
                time.sleep(2)  # 2 second delay between tournaments

        total_tournaments += year_tournaments
        total_players += year_players

        print(f"\n{year} Summary: {year_tournaments} tournaments, {year_players} player results")

    print("\n" + "=" * 100)
    print("LOADING COMPLETE")
    print("=" * 100)
    print(f"\nTotal Summary:")
    print(f"  Years processed: {end_year - start_year + 1}")
    print(f"  Tournaments loaded: {total_tournaments}")
    print(f"  Player results: {total_players}")
    print("\n" + "=" * 100)

if __name__ == "__main__":
    import sys

    # Allow command line arguments for year range
    start = 2020
    end = 2025

    if len(sys.argv) > 1:
        start = int(sys.argv[1])
    if len(sys.argv) > 2:
        end = int(sys.argv[2])

    print(f"\nStarting data load for years {start}-{end}")
    print("Press Ctrl+C to stop at any time (progress is saved continuously)\n")

    try:
        load_all_data(start, end)
    except KeyboardInterrupt:
        print("\n\nStopped by user. Progress has been saved.")
        print("You can resume by running this script again.")
    except Exception as e:
        print(f"\n\nError occurred: {e}")
        print("Progress has been saved up to this point.")
