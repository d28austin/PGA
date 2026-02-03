"""
Betting Odds Fetcher
Fetches live betting odds for PGA tournaments from various sources
"""

import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime


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

    def get_available_tournaments(self) -> List[Dict]:
        """
        Get list of available PGA tournaments with odds

        Returns:
            List of tournament dictionaries
        """
        if not self.api_key:
            print("No API key provided. Using sample data.")
            return []

        try:
            url = f"{self.base_url}/sports/golf_pga/events"
            params = {
                'apiKey': self.api_key,
                'dateFormat': 'iso'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            events = response.json()
            print(f"Found {len(events)} tournaments with available odds")
            return events

        except Exception as e:
            print(f"Error fetching tournaments: {e}")
            return []

    def get_tournament_odds(self, event_id: str, markets: List[str] = None) -> pd.DataFrame:
        """
        Get odds for a specific tournament

        Args:
            event_id: Tournament event ID
            markets: List of markets (default: ['h2h', 'outrights'])
                    'h2h' = head-to-head matchups
                    'outrights' = tournament winner odds

        Returns:
            DataFrame with player odds
        """
        if not self.api_key:
            print("No API key provided. Using sample data.")
            return self._get_sample_odds()

        if markets is None:
            markets = ['outrights']  # Tournament winner odds

        try:
            url = f"{self.base_url}/sports/golf_pga/events/{event_id}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',  # US bookmakers
                'markets': ','.join(markets),
                'oddsFormat': 'american'  # American odds format (+150, -110, etc.)
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse odds data
            odds_list = []

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
                print("No odds data found")
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

    def _get_sample_odds(self) -> pd.DataFrame:
        """
        Get sample odds data for testing (when no API key is provided)

        Returns:
            DataFrame with sample odds
        """
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
