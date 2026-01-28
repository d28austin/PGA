"""
Update 2024-2025 tournament data with earnings
Re-fetches all tournaments to ensure earnings data is included
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase
import time


def update_earnings_data():
    """Update 2024 and 2025 tournament data with earnings"""
    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    years = [2024, 2025]

    total_tournaments = 0
    total_results = 0
    tournaments_with_earnings = 0

    for year in years:
        print(f"\n{'='*60}")
        print(f"Processing {year} PGA Tour Season")
        print(f"{'='*60}\n")

        # Get tournament calendar for the year
        calendar = fetcher.get_season_calendar(year)

        if not calendar:
            print(f"[ERROR] Could not fetch {year} calendar")
            continue

        print(f"Found {len(calendar)} tournaments for {year}")

        year_tournaments = 0
        year_results = 0

        for i, tournament in enumerate(calendar, 1):
            event_id = tournament['event_id']
            name = tournament['name']

            print(f"\n[{i}/{len(calendar)}] {name} (ID: {event_id})")

            try:
                # Fetch tournament results with earnings
                results_df = fetcher.get_tournament_results(event_id, year)

                if results_df.empty:
                    print(f"  [WARN]  No results found")
                    continue

                # Add tournament name to results
                results_df['tournament_name'] = name

                # Save to database
                db.save_tournament_results(results_df)

                # Count stats
                num_players = len(results_df)
                num_with_earnings = (results_df['earnings'] > 0).sum() if 'earnings' in results_df else 0

                year_tournaments += 1
                year_results += num_players
                total_results += num_players

                if num_with_earnings > 0:
                    tournaments_with_earnings += 1

                print(f"  [OK] Saved {num_players} results ({num_with_earnings} with earnings)")

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  [ERROR] Error: {str(e)}")
                continue

        total_tournaments += year_tournaments
        print(f"\n{year} Summary: {year_tournaments} tournaments, {year_results} player results")

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total tournaments processed: {total_tournaments}")
    print(f"Total player results: {total_results}")
    print(f"Tournaments with earnings data: {tournaments_with_earnings}")
    print(f"\nDatabase updated successfully!")


if __name__ == "__main__":
    print("Updating 2024-2025 PGA Tour Data with Earnings")
    print("This will re-fetch all tournaments to ensure earnings are included\n")

    update_earnings_data()
