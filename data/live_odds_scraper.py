"""
Live Odds Scraper for PGA Tournaments
Scrapes real-time odds from betting sites

NOTE: Use responsibly and in accordance with site terms of service.
For personal/educational use only.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional, Dict, List
import json
import re
from datetime import datetime
import time


class LiveOddsScraper:
    """Scrapes live odds from multiple sources"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def scrape_draftkings_golf(self) -> pd.DataFrame:
        """
        Scrape DraftKings golf odds

        Returns:
            DataFrame with player odds
        """
        try:
            # DraftKings golf URL
            url = "https://sportsbook.draftkings.com/leagues/golf/88670846"

            print(f"Fetching DraftKings page...")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            odds_list = []

            # Method 1: Look for JSON data in script tags (most reliable)
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # Traverse JSON to find odds data
                    # DraftKings embeds odds in their page data
                    # This structure may vary
                    if isinstance(data, dict):
                        self._parse_draftkings_json(data, odds_list)
                except:
                    continue

            # Method 2: Parse visible HTML elements
            if not odds_list:
                odds_list = self._parse_draftkings_html(soup)

            if odds_list:
                df = pd.DataFrame(odds_list)
                print(f"[OK] Scraped {len(df)} odds from DraftKings")
                return df
            else:
                print("[X] No odds found - page structure may have changed")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error scraping DraftKings: {e}")
            return pd.DataFrame()

    def _parse_draftkings_json(self, data: dict, odds_list: list, depth: int = 0):
        """Recursively parse DraftKings JSON for odds data"""
        if depth > 10:  # Prevent infinite recursion
            return

        if isinstance(data, dict):
            # Look for odds-related keys
            if 'outcomes' in data:
                for outcome in data['outcomes']:
                    if isinstance(outcome, dict):
                        player = outcome.get('label', outcome.get('name', ''))
                        odds = outcome.get('oddsAmerican', outcome.get('odds', None))
                        if player and odds:
                            try:
                                odds_list.append({
                                    'player_name': player,
                                    'odds': int(odds),
                                    'bookmaker': 'DraftKings',
                                    'market': 'tournament_winner',
                                    'last_update': datetime.now().isoformat()
                                })
                            except:
                                pass

            # Recurse through nested structures
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._parse_draftkings_json(value, odds_list, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._parse_draftkings_json(item, odds_list, depth + 1)

    def _parse_draftkings_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse DraftKings HTML for odds (fallback method)"""
        odds_list = []

        # Look for common class patterns
        selectors = [
            {'player': 'sportsbook-outcome-cell__label', 'odds': 'sportsbook-odds'},
            {'player': 'event-cell__name', 'odds': 'event-cell__odd'},
            {'player': 'outcome-label', 'odds': 'outcome-odds'},
        ]

        for selector in selectors:
            players = soup.find_all(class_=re.compile(selector['player']))
            odds_elements = soup.find_all(class_=re.compile(selector['odds']))

            if players and odds_elements and len(players) == len(odds_elements):
                for player, odds in zip(players, odds_elements):
                    player_name = player.get_text(strip=True)
                    odds_text = odds.get_text(strip=True)

                    # Extract numeric odds
                    odds_match = re.search(r'([+-]?\d+)', odds_text)
                    if odds_match:
                        try:
                            odds_list.append({
                                'player_name': player_name,
                                'odds': int(odds_match.group(1)),
                                'bookmaker': 'DraftKings',
                                'market': 'tournament_winner',
                                'last_update': datetime.now().isoformat()
                            })
                        except:
                            continue

        return odds_list

    def scrape_fanduel_golf(self) -> pd.DataFrame:
        """
        Scrape FanDuel golf odds

        Returns:
            DataFrame with player odds
        """
        try:
            # FanDuel URL pattern
            url = "https://sportsbook.fanduel.com/golf"

            print(f"Fetching FanDuel page...")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            odds_list = []

            # Look for JSON data
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    self._parse_fanduel_json(data, odds_list)
                except:
                    continue

            if odds_list:
                df = pd.DataFrame(odds_list)
                print(f"[OK] Scraped {len(df)} odds from FanDuel")
                return df
            else:
                print("[X] No odds found from FanDuel")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error scraping FanDuel: {e}")
            return pd.DataFrame()

    def _parse_fanduel_json(self, data: dict, odds_list: list, depth: int = 0):
        """Parse FanDuel JSON for odds"""
        if depth > 10:
            return

        if isinstance(data, dict):
            # FanDuel might use different keys
            if 'runners' in data or 'selections' in data:
                items = data.get('runners', data.get('selections', []))
                for item in items:
                    if isinstance(item, dict):
                        player = item.get('runnerName', item.get('name', ''))
                        odds = item.get('winRunnerOdds', {}).get('americanDisplayOdds', {}).get('americanOdds')
                        if player and odds:
                            try:
                                odds_list.append({
                                    'player_name': player,
                                    'odds': int(odds),
                                    'bookmaker': 'FanDuel',
                                    'market': 'tournament_winner',
                                    'last_update': datetime.now().isoformat()
                                })
                            except:
                                pass

            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._parse_fanduel_json(value, odds_list, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._parse_fanduel_json(item, odds_list, depth + 1)

    def scrape_all_sources(self) -> pd.DataFrame:
        """
        Scrape odds from all available sources

        Returns:
            Combined DataFrame with odds from multiple bookmakers
        """
        all_odds = []

        print("=" * 60)
        print("Scraping live odds from betting sites...")
        print("=" * 60)

        # Scrape DraftKings
        dk_odds = self.scrape_draftkings_golf()
        if not dk_odds.empty:
            all_odds.append(dk_odds)
            time.sleep(2)  # Be respectful with requests

        # Scrape FanDuel
        fd_odds = self.scrape_fanduel_golf()
        if not fd_odds.empty:
            all_odds.append(fd_odds)
            time.sleep(2)

        if all_odds:
            combined_df = pd.concat(all_odds, ignore_index=True)
            print("=" * 60)
            print(f"[OK] Total: {len(combined_df)} odds from {combined_df['bookmaker'].nunique()} bookmakers")
            print(f"[OK] Players: {combined_df['player_name'].nunique()}")
            print("=" * 60)
            return combined_df
        else:
            print("=" * 60)
            print("[X] Could not scrape odds from any source")
            print("  Sites may have changed structure or blocked access")
            print("=" * 60)
            return pd.DataFrame()

    def get_best_odds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get best available odds for each player

        Args:
            df: DataFrame with odds from multiple bookmakers

        Returns:
            DataFrame with best odds per player
        """
        if df.empty:
            return df

        # Get best odds (highest for positive, least negative for negative)
        best_odds = df.groupby('player_name').agg({
            'odds': ['min', 'max', 'mean'],
            'bookmaker': lambda x: list(x)
        }).reset_index()

        best_odds.columns = ['player_name', 'min_odds', 'max_odds', 'avg_odds', 'bookmakers']

        return best_odds


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PGA Tournament Odds Scraper")
    print("=" * 60)
    print()

    scraper = LiveOddsScraper()

    # Try scraping
    odds_df = scraper.scrape_all_sources()

    if not odds_df.empty:
        print("\nTop 15 Favorites:")
        print("-" * 60)

        top_15 = odds_df.groupby('player_name')['odds'].mean().sort_values().head(15)
        for i, (player, odds) in enumerate(top_15.items(), 1):
            prob = 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
            print(f"{i:2d}. {player:30s} {odds:+6.0f} ({prob*100:5.1f}%)")

        print("\n" + "=" * 60)
        print("Scraping successful!")
        print("=" * 60)
    else:
        print("\nFalling back to sample data...")
        print("This is expected if:")
        print("  - Sites have updated their structure")
        print("  - IP has been rate limited")
        print("  - Anti-bot measures are active")
        print("\nSample data will be used instead.")
