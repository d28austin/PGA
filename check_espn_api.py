"""
Check if ESPN has an API endpoint for leaderboard data
"""

import requests
import json

def check_espn_api(tournament_id):
    """Try to find ESPN's API endpoint for tournament data"""

    # ESPN often uses this API pattern for golf data
    api_url = f"https://site.web.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard"

    params = {
        'event': tournament_id
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"Trying API endpoint: {api_url}")
    print(f"Event ID: {tournament_id}")
    print()

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        print(f"Status code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()

            # Check if we have competitors with earnings
            if 'events' in data and len(data['events']) > 0:
                event = data['events'][0]

                if 'competitions' in event and len(event['competitions']) > 0:
                    competition = event['competitions'][0]

                    if 'competitors' in competition:
                        competitors = competition['competitors']
                        print(f"Found {len(competitors)} competitors in API response")
                        print()

                        # Look at first few competitors
                        print("=" * 80)
                        print("SAMPLE COMPETITORS")
                        print("=" * 80)

                        for i, comp in enumerate(competitors[:5]):
                            athlete = comp.get('athlete', {})
                            name = athlete.get('displayName', 'Unknown')
                            position = comp.get('position', 'N/A')

                            # Check for earnings
                            statistics = comp.get('statistics', [])
                            earnings = None

                            for stat in statistics:
                                if stat.get('name') == 'earnings':
                                    earnings = stat.get('displayValue', stat.get('value'))
                                    break

                            print(f"{i+1}. {name}")
                            print(f"   Position: {position}")
                            print(f"   Earnings: {earnings}")
                            print()

                        return True

            print("No competitor data found in API response")
            return False
        else:
            print(f"API request failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("CHECKING ESPN API FOR 2022 FARMERS INSURANCE OPEN")
    print("=" * 80)
    print()

    success = check_espn_api('401353234')

    if success:
        print()
        print("=" * 80)
        print("SUCCESS! Found earnings data in API")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("API approach didn't work")
        print("=" * 80)
