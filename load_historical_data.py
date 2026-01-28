"""
Historical Data Loader
Bulk loads PGA tournament data from 2000-2025 into the database
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase
import time
from datetime import datetime


def load_historical_data(start_year: int = 2000, end_year: int = 2025):
    """
    Load all historical PGA data from start_year to end_year

    Args:
        start_year: Starting year (default 2000)
        end_year: Ending year (default 2025)
    """

    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    print(f"=" * 60)
    print(f"PGA HISTORICAL DATA LOADER")
    print(f"Loading data from {start_year} to {end_year}")
    print(f"=" * 60)

    total_tournaments = 0
    total_results = 0
    failed_tournaments = []

    for year in range(start_year, end_year + 1):
        print(f"\n{'=' * 60}")
        print(f"PROCESSING YEAR: {year}")
        print(f"{'=' * 60}")

        # Get tournament calendar for the year
        try:
            calendar = fetcher.get_season_calendar(year)

            if not calendar:
                print(f"No tournaments found for {year}")
                continue

            # Save tournaments to database
            import pandas as pd
            tournaments_df = pd.DataFrame(calendar)
            tournaments_df['tournament_id'] = tournaments_df['event_id']
            tournaments_df['tournament_name'] = tournaments_df['name']
            db.save_tournaments(tournaments_df)

            print(f"Saved {len(calendar)} tournaments for {year}")

            # Fetch results for each tournament
            for idx, tournament in enumerate(calendar, 1):
                event_id = tournament['event_id']
                name = tournament['name']

                print(f"\n[{idx}/{len(calendar)}] {name} ({event_id})...")

                # Check if we already have this data
                existing = db.get_tournament_results(event_id, year)
                if not existing.empty:
                    print(f"  Already loaded ({len(existing)} players) - skipping")
                    total_results += len(existing)
                    total_tournaments += 1
                    continue

                # Fetch results
                try:
                    results_df = fetcher.get_tournament_results(event_id, year)

                    if not results_df.empty:
                        # Save to database
                        db.save_tournament_results(results_df)
                        print(f"  OK Saved {len(results_df)} player results")

                        total_tournaments += 1
                        total_results += len(results_df)
                    else:
                        print(f"  FAIL No results found")
                        failed_tournaments.append((year, name, event_id))

                except Exception as e:
                    print(f"  FAIL Error: {e}")
                    failed_tournaments.append((year, name, event_id))

                # Rate limiting between tournaments
                time.sleep(1)

        except Exception as e:
            print(f"Error processing {year}: {e}")
            continue

        print(f"\nYear {year} complete!")
        print(f"Running totals: {total_tournaments} tournaments, {total_results} results")

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"LOADING COMPLETE!")
    print(f"{'=' * 60}")
    print(f"Total tournaments loaded: {total_tournaments}")
    print(f"Total player results: {total_results}")

    if failed_tournaments:
        print(f"\nFailed tournaments ({len(failed_tournaments)}):")
        for year, name, event_id in failed_tournaments[:10]:  # Show first 10
            print(f"  - {year}: {name} ({event_id})")
        if len(failed_tournaments) > 10:
            print(f"  ... and {len(failed_tournaments) - 10} more")

    print(f"\nData saved to: data/cache/pga_data.db")
    print(f"You can now use the Streamlit app to analyze the data!")


def load_year(year: int):
    """Load data for a specific year only"""
    load_historical_data(year, year)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load PGA historical data')
    parser.add_argument('--start', type=int, default=2020, help='Start year (default: 2020)')
    parser.add_argument('--end', type=int, default=2025, help='End year (default: 2025)')
    parser.add_argument('--year', type=int, help='Load only a specific year')

    args = parser.parse_args()

    if args.year:
        load_year(args.year)
    else:
        load_historical_data(args.start, args.end)
