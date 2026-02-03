"""
DraftKings Odds Scraper
Scrapes odds for regular PGA Tour events from DraftKings sportsbook
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional, List, Dict
import re


class DraftKingsOddsScraper:
    """Scrapes PGA tournament odds from DraftKings"""

    def __init__(self):
        self.base_url = "https://sportsbook.draftkings.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_pga_tournament_odds(self) -> pd.DataFrame:
        """
        Scrape current PGA tournament odds from DraftKings

        Returns:
            DataFrame with player names and odds
        """
        try:
            # DraftKings golf URL
            url = f"{self.base_url}/leagues/golf/88670846"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find odds elements (this is simplified - actual structure may vary)
            odds_list = []

            # Look for player names and odds
            # Note: DraftKings structure changes frequently, this is a template
            player_elements = soup.find_all('div', class_='event-cell__name')
            odds_elements = soup.find_all('span', class_='sportsbook-odds')

            for player, odds in zip(player_elements, odds_elements):
                player_name = player.get_text(strip=True)
                odds_value = odds.get_text(strip=True)

                # Convert odds to numeric
                if odds_value:
                    try:
                        odds_numeric = int(odds_value.replace('+', '').replace('−', '-'))
                        odds_list.append({
                            'player_name': player_name,
                            'odds': odds_numeric,
                            'bookmaker': 'DraftKings',
                            'market': 'tournament_winner'
                        })
                    except ValueError:
                        continue

            if odds_list:
                df = pd.DataFrame(odds_list)
                print(f"Scraped {len(df)} odds from DraftKings")
                return df
            else:
                print("No odds found - page structure may have changed")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error scraping DraftKings: {e}")
            return pd.DataFrame()

    def get_tournament_name(self) -> Optional[str]:
        """
        Get the name of the current PGA tournament

        Returns:
            Tournament name or None
        """
        try:
            url = f"{self.base_url}/leagues/golf/88670846"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for tournament name in page title or header
            title_element = soup.find('h1', class_='event-cell__name')
            if title_element:
                return title_element.get_text(strip=True)

            return None

        except Exception as e:
            print(f"Error getting tournament name: {e}")
            return None


def get_sample_phoenix_open_odds() -> pd.DataFrame:
    """
    Get sample odds for WM Phoenix Open for demonstration

    Returns:
        DataFrame with sample odds
    """
    sample_data = [
        # Favorites
        {'player_name': 'Scottie Scheffler', 'odds': 700, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Xander Schauffele', 'odds': 900, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Hideki Matsuyama', 'odds': 1200, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Patrick Cantlay', 'odds': 1400, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Collin Morikawa', 'odds': 1600, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Viktor Hovland', 'odds': 1800, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Tony Finau', 'odds': 2000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Max Homa', 'odds': 2200, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Sam Burns', 'odds': 2500, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Jordan Spieth', 'odds': 2800, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},

        # Mid-tier
        {'player_name': 'Sahith Theegala', 'odds': 3500, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Will Zalatoris', 'odds': 4000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Rickie Fowler', 'odds': 4500, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Keegan Bradley', 'odds': 5000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Justin Thomas', 'odds': 5500, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},

        # Long shots with course history
        {'player_name': 'Webb Simpson', 'odds': 6500, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Brooks Koepka', 'odds': 7000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Matt Fitzpatrick', 'odds': 8000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Tom Kim', 'odds': 9000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},
        {'player_name': 'Russell Henley', 'odds': 10000, 'bookmaker': 'DraftKings', 'market': 'tournament_winner'},

        # FanDuel odds (slightly different)
        {'player_name': 'Scottie Scheffler', 'odds': 650, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
        {'player_name': 'Xander Schauffele', 'odds': 950, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
        {'player_name': 'Hideki Matsuyama', 'odds': 1100, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
        {'player_name': 'Patrick Cantlay', 'odds': 1300, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
        {'player_name': 'Collin Morikawa', 'odds': 1500, 'bookmaker': 'FanDuel', 'market': 'tournament_winner'},
    ]

    print("Using sample WM Phoenix Open odds (market data not available via API)")
    return pd.DataFrame(sample_data)


if __name__ == "__main__":
    print("Testing DraftKings scraper...\n")

    scraper = DraftKingsOddsScraper()

    # Try to get current tournament name
    tournament = scraper.get_tournament_name()
    if tournament:
        print(f"Current tournament: {tournament}")

    # Try to scrape odds
    odds_df = scraper.get_pga_tournament_odds()

    if odds_df.empty:
        print("\nUsing sample Phoenix Open odds instead:")
        odds_df = get_sample_phoenix_open_odds()

    if not odds_df.empty:
        print(f"\nTop 10 favorites:")
        top_10 = odds_df.groupby('player_name')['odds'].mean().sort_values().head(10)
        for i, (player, odds) in enumerate(top_10.items(), 1):
            prob = 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
            print(f"{i:2d}. {player:25s} +{int(odds):5d} ({prob*100:4.1f}%)")
