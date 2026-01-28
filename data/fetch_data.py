"""
PGA Data Fetching Module
Collects player and tournament data from various sources
"""

import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import time


class PGADataFetcher:
    """Fetches PGA Tour data from public APIs"""

    def __init__(self):
        self.base_url = "https://statdata.pgatour.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_current_season_schedule(self) -> pd.DataFrame:
        """
        Fetch current season tournament schedule
        Returns: DataFrame with tournament info
        """
        try:
            year = datetime.now().year
            url = f"{self.base_url}/r/{year}/schedule.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            tournaments = []

            if 'trn' in data:
                for tournament in data['trn']:
                    tournaments.append({
                        'tournament_id': tournament.get('permNum'),
                        'tournament_name': tournament.get('trnName'),
                        'course_name': tournament.get('courses', [{}])[0].get('courseName', 'N/A'),
                        'start_date': tournament.get('date'),
                        'year': year
                    })

            return pd.DataFrame(tournaments)

        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return pd.DataFrame()

    def get_tournament_results(self, tournament_id: str, year: int) -> pd.DataFrame:
        """
        Fetch results for a specific tournament and year

        Args:
            tournament_id: Tournament permanent number
            year: Year of the tournament

        Returns: DataFrame with player results
        """
        try:
            url = f"{self.base_url}/r/{tournament_id}/{year}/leaderboard-v2.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = []

            if 'leaderboard' in data and 'players' in data['leaderboard']:
                for player in data['leaderboard']['players']:
                    results.append({
                        'player_id': player.get('player_id'),
                        'player_name': player.get('player_bio', {}).get('first_name', '') + ' ' +
                                      player.get('player_bio', {}).get('last_name', ''),
                        'position': player.get('current_position'),
                        'total_score': player.get('total'),
                        'earnings': player.get('earnings', 0),
                        'rounds_played': len(player.get('rounds', [])),
                        'tournament_id': tournament_id,
                        'year': year
                    })

            return pd.DataFrame(results)

        except Exception as e:
            print(f"Error fetching tournament {tournament_id} for {year}: {e}")
            return pd.DataFrame()

    def get_player_stats(self, player_id: str, year: int) -> Dict:
        """
        Fetch player statistics for a given year

        Args:
            player_id: Player ID
            year: Season year

        Returns: Dictionary with player stats
        """
        try:
            url = f"{self.base_url}/r/{year}/player/{player_id}/stats.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data

        except Exception as e:
            print(f"Error fetching player {player_id} stats: {e}")
            return {}

    def get_player_tournament_history(self, player_name: str, tournament_id: str,
                                     years_back: int = 5) -> pd.DataFrame:
        """
        Get a player's historical performance at a specific tournament

        Args:
            player_name: Player's name
            tournament_id: Tournament permanent number
            years_back: How many years of history to fetch

        Returns: DataFrame with historical results
        """
        current_year = datetime.now().year
        history = []

        for year in range(current_year - years_back, current_year + 1):
            results = self.get_tournament_results(tournament_id, year)
            if not results.empty:
                player_results = results[results['player_name'].str.contains(player_name, case=False, na=False)]
                history.append(player_results)
            time.sleep(0.5)  # Rate limiting

        if history:
            return pd.concat(history, ignore_index=True)
        return pd.DataFrame()

    def get_player_recent_form(self, player_id: str, num_events: int = 10) -> pd.DataFrame:
        """
        Get player's recent tournament results

        Args:
            player_id: Player ID
            num_events: Number of recent events to retrieve

        Returns: DataFrame with recent results
        """
        # This would require iterating through recent tournaments
        # Placeholder for now - will be implemented based on available data
        pass


class ESPNDataFetcher:
    """Alternative data source using ESPN APIs"""

    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga"
        self.session = requests.Session()

    def get_scoreboard(self) -> Dict:
        """Get current tournament scoreboard"""
        try:
            url = f"{self.base_url}/scoreboard"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching ESPN scoreboard: {e}")
            return {}

    def get_tournament_info(self, tournament_id: str) -> Dict:
        """Get detailed tournament information"""
        try:
            url = f"{self.base_url}/summary?event={tournament_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching tournament info: {e}")
            return {}


if __name__ == "__main__":
    # Test the fetcher
    fetcher = PGADataFetcher()
    print("Fetching current season schedule...")
    schedule = fetcher.get_current_season_schedule()
    print(f"Found {len(schedule)} tournaments")
    print(schedule.head())
