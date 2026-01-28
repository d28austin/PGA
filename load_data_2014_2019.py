"""
Load PGA Tour data from 2014-2019 with earnings included
"""

import time
import sys
from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase

def load_data():
    """Load all tournament data for 2014-2019"""

    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    years = [2014, 2015, 2016, 2017, 2018, 2019]

    print("=" * 80, flush=True)
    print("LOADING PGA TOUR DATA: 2014-2019 (WITH EARNINGS)", flush=True)
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

            if not event_id:
                print(" SKIP (no event ID)", flush=True)
                continue

            # Fetch tournament results (now includes earnings!)
            results_df = fetcher.get_tournament_results(event_id, year)

            if results_df.empty:
                print(" NO DATA", flush=True)
                continue

            # Check for earnings
            has_earnings = (results_df['earnings'].notna() & (results_df['earnings'] > 0)).sum()

            # Save to database
            import pandas as pd
            results_df['tournament_name'] = name

            # Format data for database
            save_df = pd.DataFrame({
                'player_name': results_df['player_name'],
                'tournament_name': name,
                'tournament_id': event_id,
                'year': year,
                'position': results_df['position'],
                'total_score': results_df['total_score'],
                'earnings': results_df['earnings']
            })

            db.save_tournament_results(save_df)

            year_count += 1
            year_players += len(results_df)

            print(f" OK ({len(results_df)} players, {has_earnings} with earnings)", flush=True)

            # Rate limiting
            time.sleep(0.5)

        total_tournaments += year_count
        total_players += year_players

        print(f"\n{year} Summary: {year_count} tournaments, {year_players} player results", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("COMPLETE", flush=True)
    print("=" * 80, flush=True)
    print(f"Total tournaments: {total_tournaments}", flush=True)
    print(f"Total player results: {total_players}", flush=True)
    print("", flush=True)

if __name__ == "__main__":
    load_data()
