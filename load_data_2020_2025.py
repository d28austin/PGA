"""
Load PGA Tour data from 2020-2025 with live progress updates
"""

import time
import sys
from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase

def load_data():
    """Load all tournament data for 2020-2025"""

    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    years = [2020, 2021, 2022, 2023, 2024, 2025]

    print("=" * 80, flush=True)
    print("LOADING PGA TOUR DATA: 2020-2025", flush=True)
    print("=" * 80, flush=True)
    print("This will take 20-30 minutes due to API rate limiting...", flush=True)
    print("", flush=True)

    total_tournaments = 0
    total_players = 0

    for year in years:
        print(f"\n{'=' * 80}", flush=True)
        print(f"YEAR: {year}", flush=True)
        print('=' * 80, flush=True)

        # Get calendar
        print(f"Fetching {year} calendar...", flush=True)
        calendar = fetcher.get_season_calendar(year)

        if not calendar:
            print(f"No data for {year}", flush=True)
            continue

        print(f"Found {len(calendar)} tournaments\n", flush=True)

        year_count = 0
        year_players = 0

        for i, tournament in enumerate(calendar, 1):
            event_id = tournament.get('event_id')
            name = tournament.get('name', 'Unknown')[:50]  # Truncate long names

            print(f"[{i}/{len(calendar)}] {name}...", end='', flush=True)

            # Fetch results
            results_df = fetcher.get_tournament_results(event_id, year)

            if results_df.empty:
                print(" No data", flush=True)
                continue

            # Save
            db.save_tournament_results(results_df)

            player_count = len(results_df)
            year_count += 1
            year_players += player_count

            print(f" OK ({player_count} players)", flush=True)

            # Small delay to be nice to ESPN
            if i < len(calendar):
                time.sleep(1)

        total_tournaments += year_count
        total_players += year_players

        print(f"\n{year} Complete: {year_count} tournaments, {year_players} players", flush=True)

    print(f"\n{'=' * 80}", flush=True)
    print("COMPLETE", flush=True)
    print('=' * 80, flush=True)
    print(f"Total: {total_tournaments} tournaments, {total_players} player results", flush=True)

if __name__ == "__main__":
    try:
        load_data()
    except KeyboardInterrupt:
        print("\n\nStopped by user. Progress saved.", flush=True)
    except Exception as e:
        print(f"\n\nError: {e}", flush=True)
