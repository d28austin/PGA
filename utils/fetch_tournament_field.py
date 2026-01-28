"""
Fetch current tournament field from ESPN
"""

import requests
from datetime import datetime

def fetch_tournament_field(tournament_name, year=2025):
    """
    Fetch the tournament field (list of players) from ESPN for the current year

    Args:
        tournament_name: Name of the tournament
        year: Year to fetch (default 2025)

    Returns:
        list: List of player names in the field, or empty list if not available
    """
    # Try to find the tournament ID for this year
    try:
        # Use ESPN's API to search for upcoming tournaments
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
        params = {
            'league': 'pga',
            'dates': year
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()

        if 'events' not in data or len(data['events']) == 0:
            return []

        # Look for matching tournament
        for event in data['events']:
            event_name = event.get('name', '')

            # Check if names match (case-insensitive, partial match)
            if tournament_name.lower() in event_name.lower() or event_name.lower() in tournament_name.lower():

                if 'competitions' in event and len(event['competitions']) > 0:
                    competition = event['competitions'][0]

                    if 'competitors' in competition:
                        competitors = competition['competitors']

                        # Extract player names
                        field = []
                        for competitor in competitors:
                            if 'athlete' in competitor:
                                player_name = competitor['athlete'].get('displayName')
                                if player_name:
                                    field.append(player_name)

                        return sorted(field)

        return []

    except Exception as e:
        print(f"Error fetching tournament field: {e}")
        return []


def fetch_field_by_tournament_id(tournament_id):
    """
    Fetch tournament field using a specific tournament ID

    Args:
        tournament_id: ESPN tournament ID

    Returns:
        list: List of player names in the field
    """
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
        params = {
            'league': 'pga',
            'event': tournament_id
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()

        if 'events' not in data or len(data['events']) == 0:
            return []

        event = data['events'][0]

        if 'competitions' not in event or len(event['competitions']) == 0:
            return []

        competition = event['competitions'][0]

        if 'competitors' not in competition:
            return []

        competitors = competition['competitors']

        # Extract player names
        field = []
        for competitor in competitors:
            if 'athlete' in competitor:
                player_name = competitor['athlete'].get('displayName')
                if player_name:
                    field.append(player_name)

        return sorted(field)

    except Exception as e:
        print(f"Error fetching tournament field: {e}")
        return []


if __name__ == "__main__":
    # Test with a known tournament
    print("Testing tournament field fetch...")
    print()

    # Try to fetch The Sentry field (usually first tournament of year)
    field = fetch_field_by_tournament_id('401580329')

    if field:
        print(f"Found {len(field)} players in the field")
        print()
        print("Sample players:")
        for player in field[:10]:
            print(f"  - {player}")
    else:
        print("No field data available")
