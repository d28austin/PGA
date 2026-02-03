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
        Get odds for a specific tournament

        Args:
            tournament_name: Name of the tournament (e.g., "Masters Tournament")

        Returns:
            DataFrame with player odds
        """
        # First, check if we have scraped odds in the database
        scraped_odds = self.get_scraped_odds_from_db(tournament_name)
        if not scraped_odds.empty:
            return scraped_odds

        if not self.api_key:
            print("No API key provided. Using sample data.")
            return self._get_sample_odds(tournament_name)

        # Get sport key for this tournament
        sport_key = self.get_sport_key_for_tournament(tournament_name)

        if not sport_key:
            # For non-major tournaments, check for recent scraped odds or use sample data
            print(f"'{tournament_name}' is not a major championship.")
            print("The Odds API only covers: Masters, PGA Championship, US Open, The Open")

            # Try to get any recent scraped odds
            recent_scraped = self.get_scraped_odds_from_db()
            if not recent_scraped.empty:
                print("Using recently scraped odds from database...")
                return recent_scraped

            print("Using sample data for demonstration...")
            print("TIP: Run 'python scrape_weekly_odds.py' to get live odds!")
            return self._get_sample_odds(tournament_name)

        try:
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',  # US bookmakers
                'oddsFormat': 'american'  # American odds format (+150, -110, etc.)
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse odds data - API returns list of events
            odds_list = []

            # Handle list response (each item is an event)
            if isinstance(data, list):
                for event in data:
                    for bookmaker in event.get('bookmakers', []):
                        bookmaker_name = bookmaker.get('title')

                        for market in bookmaker.get('markets', []):
                            market_type = market.get('key')

                            for outcome in market.get('outcomes', []):
                                odds_list.append({
                                    'player_name': outcome.get('name'),
                                    'bookmaker': bookmaker_name,
                                    'market': market_type,
                                    'odds': outcome.get('price'),
                                    'last_update': bookmaker.get('last_update')
                                })
            # Handle dict response (single event)
            elif isinstance(data, dict):
                for bookmaker in data.get('bookmakers', []):
                    bookmaker_name = bookmaker.get('title')

                    for market in bookmaker.get('markets', []):
                        market_type = market.get('key')

                        for outcome in market.get('outcomes', []):
                            odds_list.append({
                                'player_name': outcome.get('name'),
                                'bookmaker': bookmaker_name,
                                'market': market_type,
                                'odds': outcome.get('price'),
                                'last_update': bookmaker.get('last_update')
                            })

            if odds_list:
                df = pd.DataFrame(odds_list)
                print(f"Retrieved odds for {df['player_name'].nunique()} players from {df['bookmaker'].nunique()} bookmakers")
                return df
            else:
                print("No odds data found for this tournament")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error fetching odds: {e}")
            return pd.DataFrame()

    def get_best_odds_summary(self, event_id: str) -> pd.DataFrame:
        """
        Get best available odds for each player across all bookmakers

        Args:
            event_id: Tournament event ID

        Returns:
            DataFrame with best odds for each player
        """
        odds_df = self.get_tournament_odds(event_id)

        if odds_df.empty:
            return pd.DataFrame()

        # Get best odds for each player (highest positive or least negative)
        summary = odds_df.groupby('player_name').agg({
            'odds': ['min', 'max', 'mean'],
            'bookmaker': 'count'
        }).reset_index()

        summary.columns = ['player_name', 'min_odds', 'max_odds', 'avg_odds', 'num_books']

        # Convert American odds to implied probability
        def american_to_probability(odds):
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)

        summary['implied_prob_min'] = summary['min_odds'].apply(american_to_probability)
        summary['implied_prob_max'] = summary['max_odds'].apply(american_to_probability)
        summary['implied_prob_avg'] = summary['avg_odds'].apply(american_to_probability)

        # Sort by best odds (lowest implied probability = best value)
        summary = summary.sort_values('implied_prob_avg', ascending=False)

        return summary

    def get_top_10_odds(self, event_id: str) -> pd.DataFrame:
        """
        Get top 10 finish odds if available

        Args:
            event_id: Tournament event ID

        Returns:
            DataFrame with top 10 odds
        """
        # Many books offer top 5, top 10, top 20 markets
        odds_df = self.get_tournament_odds(event_id, markets=['outrights', 'top_5', 'top_10'])

        if odds_df.empty:
            return pd.DataFrame()

        # Filter for top 10 market
        top_10_df = odds_df[odds_df['market'].str.contains('top_10', case=False, na=False)]

        if top_10_df.empty:
            print("No top 10 odds available")
            return pd.DataFrame()

        return top_10_df

    def _get_sample_odds(self, tournament_name: str = None) -> pd.DataFrame:
        """
        Get sample odds data for testing (when no API key is provided)

        Args:
            tournament_name: Name of tournament (to provide tournament-specific samples)

        Returns:
            DataFrame with sample odds
        """
        # Phoenix Open specific odds
        if tournament_name and 'phoenix' in tournament_name.lower():
            sample_data = [
                # DraftKings
                {'player_name': 'Scottie Scheffler', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 700, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Xander Schauffele', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 900, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Hideki Matsuyama', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 1200, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Patrick Cantlay', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 1400, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Collin Morikawa', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 1600, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Viktor Hovland', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 1800, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Tony Finau', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 2000, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Max Homa', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 2200, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Sam Burns', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 2500, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Jordan Spieth', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 2800, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Sahith Theegala', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 3500, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Will Zalatoris', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 4000, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Rickie Fowler', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 4500, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Justin Thomas', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 5500, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Brooks Koepka', 'bookmaker': 'DraftKings', 'market': 'tournament_winner', 'odds': 7000, 'last_update': datetime.now().isoformat()},

                # FanDuel (slightly different odds)
                {'player_name': 'Scottie Scheffler', 'bookmaker': 'FanDuel', 'market': 'tournament_winner', 'odds': 650, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Xander Schauffele', 'bookmaker': 'FanDuel', 'market': 'tournament_winner', 'odds': 950, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Hideki Matsuyama', 'bookmaker': 'FanDuel', 'market': 'tournament_winner', 'odds': 1100, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Patrick Cantlay', 'bookmaker': 'FanDuel', 'market': 'tournament_winner', 'odds': 1300, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Collin Morikawa', 'bookmaker': 'FanDuel', 'market': 'tournament_winner', 'odds': 1500, 'last_update': datetime.now().isoformat()},
            ]
            print(f"Using sample WM Phoenix Open odds (regular tour events not available via API)")
        else:
            # Generic sample odds
            sample_data = [
                {'player_name': 'Scottie Scheffler', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 450, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Rory McIlroy', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 800, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Jon Rahm', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 900, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Viktor Hovland', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 1200, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Xander Schauffele', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 1400, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Patrick Cantlay', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 1600, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Collin Morikawa', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 1800, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Max Homa', 'bookmaker': 'DraftKings', 'market': 'outrights', 'odds': 2000, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Scottie Scheffler', 'bookmaker': 'FanDuel', 'market': 'outrights', 'odds': 425, 'last_update': datetime.now().isoformat()},
                {'player_name': 'Rory McIlroy', 'bookmaker': 'FanDuel', 'market': 'outrights', 'odds': 850, 'last_update': datetime.now().isoformat()},
            ]
            print("Using sample odds data (no API key provided)")

        return pd.DataFrame(sample_data)

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
