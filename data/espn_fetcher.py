"""
ESPN PGA Data Fetcher
Fetches historical and current PGA Tour data from ESPN APIs
"""

import requests
import pandas as pd
from typing import Dict, List, Optional
import time
from datetime import datetime


class ESPNPGAFetcher:
    """Fetches PGA Tour data from ESPN API"""

    def __init__(self):
        self.base_url = "http://sports.core.api.espn.com/v2/sports/golf/leagues/pga"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_season_calendar(self, year: int) -> List[Dict]:
        """
        Get tournament calendar for a specific year

        Args:
            year: Season year

        Returns: List of tournament dictionaries
        """
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard?dates={year}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            tournaments = []

            if 'leagues' in data and len(data['leagues']) > 0:
                league = data['leagues'][0]
                if 'calendar' in league:
                    for event in league['calendar']:
                        tournaments.append({
                            'event_id': event.get('id'),
                            'name': event.get('label'),
                            'start_date': event.get('startDate'),
                            'end_date': event.get('endDate'),
                            'year': year
                        })

            print(f"Found {len(tournaments)} tournaments for {year}")
            return tournaments

        except Exception as e:
            print(f"Error fetching {year} calendar: {e}")
            return []

    def get_competitor_details(self, competitor_ref: str) -> Optional[Dict]:
        """Fetch full competitor details from reference URL"""
        try:
            response = self.session.get(competitor_ref, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching competitor: {e}")
        return None

    def get_tournament_par(self, event_id: str) -> Optional[Dict]:
        """
        Get tournament par information including courses
        Note: Rounds will need to be determined from actual score data

        Args:
            event_id: ESPN event ID

        Returns: Dict with par info: {'par_per_round': 72, 'courses': [...]}
        """
        try:
            event_url = f"{self.base_url}/events/{event_id}"
            response = self.session.get(event_url, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if 'courses' not in data or not data['courses']:
                return None

            courses = data['courses']
            course_pars = []

            for course in courses:
                par = course.get('shotsToPar')
                if par:
                    course_pars.append({
                        'name': course.get('displayName', 'Unknown'),
                        'par': par,
                        'par_in': course.get('parIn'),
                        'par_out': course.get('parOut')
                    })

            if not course_pars:
                return None

            # Calculate average par if multiple courses
            avg_par = sum(c['par'] for c in course_pars) / len(course_pars)

            return {
                'par_per_round': int(round(avg_par)),
                'courses': course_pars,
                'num_courses': len(course_pars)
            }

        except Exception as e:
            print(f"Error fetching tournament par for {event_id}: {e}")
            return None

    def get_tournament_results(self, event_id: str, year: int) -> pd.DataFrame:
        """
        Fetch tournament results including all players and their positions
        Uses leaderboard API to get earnings data as well

        Args:
            event_id: ESPN event ID
            year: Tournament year

        Returns: DataFrame with player results
        """
        try:
            # Use leaderboard API which includes earnings
            leaderboard_url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
            params = {'league': 'pga', 'event': event_id}
            response = self.session.get(leaderboard_url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"Event {event_id} not available (status {response.status_code})")
                return pd.DataFrame()

            data = response.json()

            # Navigate to competitors in leaderboard API structure
            if 'events' not in data or len(data['events']) == 0:
                print(f"No event data found for {event_id}")
                return pd.DataFrame()

            event = data['events'][0]
            tournament_name = event.get('name', '')

            if 'competitions' not in event or len(event['competitions']) == 0:
                print(f"No competitions found for event {event_id}")
                return pd.DataFrame()

            competition = event['competitions'][0]

            if 'competitors' not in competition:
                print(f"No competitors found for event {event_id}")
                return pd.DataFrame()

            competitors = competition['competitors']
            results = []

            print(f"Processing {len(competitors)} players for event {event_id}...")

            for competitor in competitors:
                try:
                    # Get player info
                    if 'athlete' not in competitor:
                        continue

                    athlete = competitor['athlete']
                    player_id = athlete.get('id')
                    player_name = athlete.get('displayName', 'Unknown')

                    # Get position from status
                    position = None
                    if 'status' in competitor and 'position' in competitor['status']:
                        pos_data = competitor['status']['position']
                        position = pos_data.get('displayName') or pos_data.get('id')

                    # Get score
                    total_score = None
                    if 'score' in competitor:
                        score_data = competitor['score']
                        if isinstance(score_data, dict):
                            total_score = score_data.get('value')
                        else:
                            total_score = score_data

                    # Get earnings (this is the key addition)
                    earnings = competitor.get('earnings', 0)
                    if earnings:
                        earnings = int(earnings)
                    else:
                        earnings = 0

                    results.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'position': position,
                        'total_score': total_score,
                        'earnings': earnings,
                        'tournament_id': event_id,
                        'tournament_name': tournament_name,
                        'year': year
                    })

                except Exception as e:
                    print(f"Error processing competitor: {e}")
                    continue

            print(f"Successfully fetched {len(results)} results for event {event_id} (with earnings)")
            return pd.DataFrame(results)

        except Exception as e:
            print(f"Error fetching tournament {event_id}: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # Test the fetcher
    fetcher = ESPNPGAFetcher()

    print("Testing ESPN PGA Fetcher...")
    print("\n1. Getting 2024 calendar...")
    calendar = fetcher.get_season_calendar(2024)

    if calendar:
        print(f"First tournament: {calendar[0]['name']}")

        print("\n2. Getting results for first tournament...")
        results = fetcher.get_tournament_results(calendar[0]['event_id'], 2024)

        if not results.empty:
            print(f"\nResults preview:")
            print(results.head(10))
            print(f"\nTotal players: {len(results)}")
