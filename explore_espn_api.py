"""
Explore ESPN API for historical PGA data
"""

import requests
import json

def explore_event_details(event_id):
    """Get detailed information about a specific event"""
    print(f"\nExploring event {event_id}...")

    # Try different ESPN API endpoints
    endpoints = [
        f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/summary?event={event_id}",
        f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard?event={event_id}",
        f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}",
    ]

    for url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            print(f"\nURL: {url}")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Keys: {list(data.keys())[:10]}")

                # Look for player/competition data
                if 'leaderboard' in data:
                    print("Found leaderboard data!")
                    leaderboard = data['leaderboard']
                    if 'players' in leaderboard:
                        print(f"Number of players: {len(leaderboard['players'])}")
                        if leaderboard['players']:
                            player = leaderboard['players'][0]
                            print(f"Sample player keys: {list(player.keys())}")

                if 'header' in data:
                    header = data['header']
                    if 'competition' in header:
                        print(f"Competition info available")

                # Save sample for inspection
                with open(f'sample_event_{event_id}.json', 'w') as f:
                    json.dump(data, f, indent=2)
                    print(f"Saved to sample_event_{event_id}.json")
                    break

        except Exception as e:
            print(f"Error: {e}")

def test_historical_events():
    """Test if we can access historical tournament data"""
    print("\nTesting historical event access...")

    # Known tournament IDs (these are examples)
    # The Masters 2024: 401811933
    # The Masters 2023: 401465614
    # The Masters 2022: 401408425

    test_events = [
        ("2024 Masters", "401811933"),
        ("2023 Masters", "401465514"),  # Example ID
        ("2024 Players", "401811934"),  # Example ID
    ]

    for name, event_id in test_events:
        print(f"\nTrying {name} (ID: {event_id})...")
        url = f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/summary?event={event_id}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'header' in data and 'competition' in data['header']:
                    comp = data['header']['competition']
                    print(f"  Success! Tournament: {comp.get('name', 'N/A')}")
                    print(f"  Date: {comp.get('date', 'N/A')}")

                    if 'competitors' in comp:
                        print(f"  Players: {len(comp['competitors'])}")
            else:
                print(f"  Status {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

def get_tournament_schedule(year=2024):
    """Try to get tournament schedule for a specific year"""
    print(f"\nTrying to get {year} schedule...")

    urls = [
        f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard?dates={year}",
        f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/seasons/{year}",
        f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/seasons/{year}/types/1",
    ]

    for url in urls:
        try:
            print(f"\nURL: {url}")
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Keys: {list(data.keys())[:10]}")

                # Save for inspection
                filename = f"schedule_{year}_{urls.index(url)}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Saved to {filename}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Get current event details
    explore_event_details("401811930")  # Current Farmers Insurance Open

    # Test historical access
    test_historical_events()

    # Try to get schedule
    get_tournament_schedule(2024)
    get_tournament_schedule(2023)
