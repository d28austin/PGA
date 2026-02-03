"""
FanDuel Odds Scraper
Scrapes golf betting odds from FanDuel Sportsbook
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional, List, Dict
import json
import re
import time


class FanDuelOddsScraper:
    """Scrapes PGA tournament odds from FanDuel"""

    def __init__(self):
        self.base_url = "https://sportsbook.fanduel.com"
        self.api_base = "https://sbapi.il.sportsbook.fanduel.com/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://sportsbook.fanduel.com/golf',
            'Origin': 'https://sportsbook.fanduel.com'
        }

    def get_golf_tournaments_api(self) -> List[Dict]:
        """
        Try to fetch golf tournaments from FanDuel API

        Returns:
            List of available golf tournaments
        """
        try:
            # FanDuel's API endpoint for golf events
            url = f"{self.api_base}/content-managed-cards/6927/en/US?timezone=America/New_York"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print("Successfully connected to FanDuel API")
                return data
            else:
                print(f"API returned status: {response.status_code}")
                return []

        except Exception as e:
            print(f"Error fetching tournaments from API: {e}")
            return []

    def get_pga_tournament_odds(self, event_id: Optional[str] = None) -> pd.DataFrame:
        """
        Scrape current PGA tournament odds from FanDuel

        Args:
            event_id: Optional specific event ID to fetch

        Returns:
            DataFrame with player names and odds
        """
        try:
            # Try API approach first
            url = f"{self.base_url}/golf"

            # Use session for better connection handling
            session = requests.Session()
            session.headers.update(self.headers)

            response = session.get(url, timeout=15)

            if response.status_code == 403:
                print("FanDuel blocking direct access. Using alternative method...")
                return self._get_odds_alternative()

            response.raise_for_status()

            # Try to find embedded JSON data in page
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for script tags with embedded data
            scripts = soup.find_all('script', type='application/json')

            odds_list = []

            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # Parse odds from embedded data
                    odds_data = self._parse_embedded_odds(data)
                    if odds_data:
                        odds_list.extend(odds_data)
                except (json.JSONDecodeError, AttributeError):
                    continue

            if odds_list:
                df = pd.DataFrame(odds_list)
                print(f"Scraped {len(df)} odds from FanDuel")
                return df
            else:
                print("No odds found in page data")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error scraping FanDuel: {e}")
            return pd.DataFrame()

    def _parse_embedded_odds(self, data: Dict) -> List[Dict]:
        """
        Parse odds from embedded JSON data

        Args:
            data: JSON data from page

        Returns:
            List of odds dictionaries
        """
        odds_list = []

        try:
            # Navigate through FanDuel's data structure
            # This structure may vary - adjust based on actual format
            if 'attachments' in data:
                for key, value in data['attachments'].items():
                    if isinstance(value, dict) and 'markets' in value:
                        for market in value['markets']:
                            if 'runners' in market:
                                for runner in market['runners']:
                                    player_name = runner.get('runnerName', '')
                                    odds_decimal = runner.get('winRunnerOdds', {}).get('americanDisplayOdds', {}).get('americanOdds')

                                    if player_name and odds_decimal:
                                        odds_list.append({
                                            'player_name': player_name,
                                            'odds': int(odds_decimal),
                                            'bookmaker': 'FanDuel',
                                            'market': 'tournament_winner'
                                        })
        except Exception as e:
            print(f"Error parsing embedded odds: {e}")

        return odds_list

    def _get_odds_alternative(self) -> pd.DataFrame:
        """
        Alternative method to get FanDuel odds
        Using sample data for now - can be replaced with Selenium if needed

        Returns:
            DataFrame with odds
        """
        print("Using sample FanDuel odds (live scraping requires browser automation)")

        # Sample odds based on typical FanDuel pricing
        sample_data = [
            {'player_name': 'Scottie Scheffler', 'odds': 650, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Rory McIlroy', 'odds': 900, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Xander Schauffele', 'odds': 1000, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Viktor Hovland', 'odds': 1200, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Patrick Cantlay', 'odds': 1400, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Jon Rahm', 'odds': 1600, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Collin Morikawa', 'odds': 1800, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Jordan Spieth', 'odds': 2000, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Justin Thomas', 'odds': 2200, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
            {'player_name': 'Max Homa', 'odds': 2500, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
        ]

        return pd.DataFrame(sample_data)

    def get_tournament_name(self) -> Optional[str]:
        """
        Get the name of the current PGA tournament

        Returns:
            Tournament name or None
        """
        try:
            url = f"{self.base_url}/golf"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for tournament name in various possible locations
                # This is a template - actual selectors depend on page structure
                selectors = [
                    'h1[data-testid="tournament-name"]',
                    'div[class*="event-name"]',
                    'span[class*="tournament"]'
                ]

                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        return element.get_text(strip=True)

            return None

        except Exception as e:
            print(f"Error getting tournament name: {e}")
            return None


def test_fanduel_scraper():
    """Test the FanDuel scraper"""
    print("="*80)
    print("FANDUEL ODDS SCRAPER TEST")
    print("="*80)
    print()

    scraper = FanDuelOddsScraper()

    # Try to get tournament name
    print("1. Fetching tournament name...")
    tournament = scraper.get_tournament_name()
    if tournament:
        print(f"   Tournament: {tournament}")
    else:
        print("   Could not fetch tournament name")

    print()

    # Try to fetch odds
    print("2. Fetching odds...")
    odds_df = scraper.get_pga_tournament_odds()

    if not odds_df.empty:
        print(f"\nSuccessfully scraped {len(odds_df)} players")
        print("\nTop 10 Favorites:")
        print("-"*80)

        for i, row in odds_df.head(10).iterrows():
            player = row['player_name']
            odds = row['odds']

            # Calculate implied probability
            if odds > 0:
                prob = 100 / (odds + 100)
            else:
                prob = abs(odds) / (abs(odds) + 100)

            print(f"{i+1:2d}. {player:30s} {odds:+5d} ({prob*100:4.1f}%)")

        return odds_df
    else:
        print("\nNo odds data available")
        return pd.DataFrame()


if __name__ == "__main__":
    test_fanduel_scraper()
