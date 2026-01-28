"""
Try different ESPN API patterns
"""

import requests
import json

def try_api_patterns(tournament_id):
    """Try various ESPN API endpoint patterns"""

    patterns = [
        f"https://www.espn.com/golf/leaderboard/data?tournamentId={tournament_id}",
        f"https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard?league=pga&event={tournament_id}",
        f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{tournament_id}",
        f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{tournament_id}/competitions/{tournament_id}/competitors",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for i, url in enumerate(patterns, 1):
        print(f"[{i}/{len(patterns)}] Trying: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  SUCCESS! Got JSON response")
                    print(f"  Keys: {list(data.keys())[:10]}")
                    print()

                    # Save to file for inspection
                    with open(f'api_response_{i}.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"  Saved to api_response_{i}.json")
                    print()

                    return True
                except:
                    print(f"  Response is not JSON")
            else:
                print()

        except Exception as e:
            print(f"  Error: {e}")
            print()

    return False

if __name__ == "__main__":
    print("=" * 80)
    print("TRYING DIFFERENT ESPN API PATTERNS")
    print("=" * 80)
    print()

    success = try_api_patterns('401353234')

    if not success:
        print()
        print("None of the API patterns worked")
