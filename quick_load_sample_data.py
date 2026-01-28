"""
Quick Sample Data Loader
Loads just a few tournaments to demonstrate the system
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase
import pandas as pd


def load_sample_data():
    """Load sample data from recent tournaments"""

    fetcher = ESPNPGAFetcher()
    db = PGADatabase()

    print("Loading sample PGA data for demonstration...")
    print("=" * 60)

    # Load 2024 tournaments
    print("\nFetching 2024 tournament calendar...")
    calendar = fetcher.get_season_calendar(2024)

    if not calendar:
        print("Error: Could not fetch calendar")
        return

    # Save tournament list
    tournaments_df = pd.DataFrame(calendar)
    tournaments_df['tournament_id'] = tournaments_df['event_id']
    tournaments_df['tournament_name'] = tournaments_df['name']
    db.save_tournaments(tournaments_df)
    print(f"Saved {len(calendar)} tournament entries")

    # Load data for first 5 tournaments as sample
    sample_tournaments = calendar[:5]

    print(f"\nLoading results for {len(sample_tournaments)} sample tournaments...")

    for idx, tournament in enumerate(sample_tournaments, 1):
        event_id = tournament['event_id']
        name = tournament['name']

        print(f"\n[{idx}/{len(sample_tournaments)}] {name}...")

        try:
            results_df = fetcher.get_tournament_results(event_id, 2024)

            if not results_df.empty:
                db.save_tournament_results(results_df)
                print(f"  OK - Saved {len(results_df)} player results")
            else:
                print(f"  SKIP - No results available")

        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print("Sample data loaded successfully!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Run the Streamlit app: python -m streamlit run app.py")
    print("2. Load full historical data: python load_historical_data.py --start 2020 --end 2025")


if __name__ == "__main__":
    load_sample_data()
