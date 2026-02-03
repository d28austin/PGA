"""
Betting Odds Fetcher
Fetches live betting odds for PGA tournaments from various sources
"""

import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import os


class OddsFetcher:
    """Fetches betting odds from multiple sources"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize odds fetcher

        Args:
            api_key: API key for The Odds API (get free key at https://the-odds-api.com/)
        """
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"

        # Map tournament names to API sport keys
        self.tournament_map = {
            'Masters Tournament': 'golf_masters_tournament_winner',
            'The Masters': 'golf_masters_tournament_winner',
            'Masters': 'golf_masters_tournament_winner',
            'PGA Championship': 'golf_pga_championship_winner',
            'U.S. Open': 'golf_us_open_winner',
            'US Open': 'golf_us_open_winner',
            'United States Open Championship': 'golf_us_open_winner',
            'The Open Championship': 'golf_the_open_championship_winner',
            'The Open': 'golf_the_open_championship_winner',
            'British Open': 'golf_the_open_championship_winner'
        }

    def get_available_golf_sports(self) -> List[Dict]:
        """
        Get list of available golf sports/tournaments with odds

        Returns:
            List of golf sport dictionaries
        """
        if not self.api_key:
            print("No API key provided. Using sample data.")
            return []

        try:
            url = f"{self.base_url}/sports"
            params = {
                'apiKey': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            all_sports = response.json()
            # Filter for golf sports
            golf_sports = [s for s in all_sports if 'golf' in s.get('key', '').lower()]

            print(f"Found {len(golf_sports)} golf tournaments with available odds")
            return golf_sports

        except Exception as e:
            print(f"Error fetching tournaments: {e}")
            return []

    def get_sport_key_for_tournament(self, tournament_name: str) -> Optional[str]:
        """
        Get the API sport key for a tournament name

        Args:
            tournament_name: Name of the tournament

        Returns:
            Sport key or None if not found
        """
        # Check exact matches first
        if tournament_name in self.tournament_map:
            return self.tournament_map[tournament_name]

        # Check partial matches
        for key, sport_key in self.tournament_map.items():
            if key.lower() in tournament_name.lower() or tournament_name.lower() in key.lower():
                return sport_key

        return None

    def get_scraped_odds_from_db(self, tournament_name: str = None) -> pd.DataFrame:
        """
        Get odds from weekly scraping (if available)

        Args:
            tournament_name: Optional tournament name to filter

        Returns:
            DataFrame with scraped odds or empty DataFrame
        """
        try:
            import sqlite3
            db_path = "data/cache/pga_data.db"

            if not os.path.exists(db_path):
                return pd.DataFrame()

            conn = sqlite3.connect(db_path)

            # Check if table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_odds'")
            if not cursor.fetchone():
                conn.close()
                return pd.DataFrame()

            # Get most recent odds
            if tournament_name:
                query = """
                    SELECT player_name, odds, bookmaker, tournament, scraped_at
                    FROM weekly_odds
                    WHERE tournament LIKE ?
                    ORDER BY created_at DESC
                """
                df = pd.read_sql(query, conn, params=(f'%{tournament_name}%',))
            else:
                # Get most recent scraping session
                query = """
                    SELECT player_name, odds, bookmaker, tournament, scraped_at
                    FROM weekly_odds
                    WHERE scraped_at = (SELECT MAX(scraped_at) FROM weekly_odds)
                """
                df = pd.read_sql(query, conn)

            conn.close()

            if not df.empty:
                df['market'] = 'tournament_winner'
                df['last_update'] = df['scraped_at']
                print(f"Found {len(df)} scraped odds from database (last updated: {df['scraped_at'].iloc[0]})")

            return df

        except Exception as e:
            print(f"Error loading scraped odds: {e}")
            return pd.DataFrame()

    def get_tournament_odds(self, tournament_name: str) -> pd.DataFrame:
        """
        Get odds for a specific tournament (from scraped database only)

        Args:
            tournament_name: Name of the tournament

        Returns:
            DataFrame with player odds from scraped data, or empty DataFrame
        """
        # Only check scraped odds in database
        scraped_odds = self.get_scraped_odds_from_db(tournament_name)

        if not scraped_odds.empty:
            return scraped_odds

        # No scraped odds found
        print(f"No scraped odds found for '{tournament_name}'")
        print("TIP: Run 'python scrape_weekly_odds.py' to get live odds!")
        return pd.DataFrame()

    @staticmethod
    def calculate_value(historical_win_rate: float, implied_probability: float) -> float:
        """
        Calculate betting value based on historical performance vs odds

        Args:
            historical_win_rate: Player's historical win rate at this tournament
            implied_probability: Implied probability from betting odds

        Returns:
            Value score (positive = good value, negative = overpriced)
        """
        if implied_probability == 0:
            return 0

        # Value = (Historical Win Rate - Implied Probability) / Implied Probability
        # This shows percentage edge
        return ((historical_win_rate - implied_probability) / implied_probability) * 100

    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        """
        Convert American odds to decimal odds

        Args:
            american_odds: American odds format (+150, -110, etc.)

        Returns:
            Decimal odds
        """
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    @staticmethod
    def american_to_probability(american_odds: int) -> float:
        """
        Convert American odds to implied probability

        Args:
            american_odds: American odds format (+150, -110, etc.)

        Returns:
            Implied probability (0-1)
        """
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)


if __name__ == "__main__":
    # Test the odds fetcher
    fetcher = OddsFetcher()  # No API key = uses sample data

    print("\n1. Testing with sample data (no API key):")
    sample_odds = fetcher._get_sample_odds()
    print(sample_odds)

    print("\n2. Calculating implied probabilities:")
    for odds in [450, 800, 1200, -150, -110]:
        prob = fetcher.american_to_probability(odds)
        decimal = fetcher.american_to_decimal(odds)
        print(f"American: {odds:+5d} -> Decimal: {decimal:.2f} -> Probability: {prob:.1%}")

    print("\n3. Calculating value:")
    # Example: Player has 8% historical win rate, odds imply 5% probability
    value = fetcher.calculate_value(0.08, 0.05)
    print(f"Historical: 8%, Implied: 5% -> Value: {value:+.1f}% edge")
