"""
Load missing years: 2021, 2023, 2025
"""

import time
import sys
from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase

def load_year(year):
    """Load a single year"""
    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    print(f"\n{'=' * 80}", flush=True)
    print(f"YEAR: {year}", flush=True)
    print('=' * 80, flush=True)

    print(f"Fetching {year} calendar...", flush=True)

    # Retry calendar fetch up to 3 times
    calendar = None
    for attempt in range(3):
        try:
            calendar = fetcher.get_season_calendar(year)
            if calendar:
                break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}", flush=True)
            if attempt < 2:
                time.sleep(5)  # Wait 5 seconds before retry

    if not calendar:
        print(f"Failed to fetch {year} calendar after 3 attempts", flush=True)
        return 0, 0

    print(f"Found {len(calendar)} tournaments\n", flush=True)

    year_count = 0
    year_players = 0

    for i, tournament in enumerate(calendar, 1):
        event_id = tournament.get('event_id')
        name = tournament.get('name', 'Unknown')[:50]

        print(f"[{i}/{len(calendar)}] {name}...", end='', flush=True)

        results_df = fetcher.get_tournament_results(event_id, year)

        if results_df.empty:
            print(" No data", flush=True)
            continue

        db.save_tournament_results(results_df)

        player_count = len(results_df)
        year_count += 1
        year_players += player_count

        print(f" OK ({player_count} players)", flush=True)

        if i < len(calendar):
            time.sleep(1)

    print(f"\n{year} Complete: {year_count} tournaments, {year_players} players", flush=True)
    return year_count, year_players

if __name__ == "__main__":
    missing_years = [2021, 2023, 2025]

    print("=" * 80, flush=True)
    print("LOADING MISSING YEARS: 2021, 2023, 2025", flush=True)
    print("=" * 80, flush=True)

    total_tournaments = 0
    total_players = 0

    for year in missing_years:
        try:
            t, p = load_year(year)
            total_tournaments += t
            total_players += p
        except KeyboardInterrupt:
            print(f"\n\nStopped by user.", flush=True)
            break
        except Exception as e:
            print(f"\nError loading {year}: {e}", flush=True)

    print(f"\n{'=' * 80}", flush=True)
    print("COMPLETE", flush=True)
    print('=' * 80, flush=True)
    print(f"Total: {total_tournaments} tournaments, {total_players} players", flush=True)
