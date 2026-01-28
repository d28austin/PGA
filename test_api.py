"""
Test script to verify PGA API endpoints are working
"""

import requests
import json
from datetime import datetime

def test_pga_api():
    """Test various PGA Tour API endpoints"""

    print("Testing PGA Tour API endpoints...\n")

    # Test 1: Current season schedule
    print("1. Testing current season schedule...")
    year = datetime.now().year
    url = f"https://statdata.pgatour.com/r/{year}/schedule.json"

    try:
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'trn' in data and len(data['trn']) > 0:
                print(f"   ✓ Success! Found {len(data['trn'])} tournaments")
                print(f"   Sample tournament: {data['trn'][0].get('trnName', 'N/A')}")
            else:
                print("   ✗ No tournament data in response")
        else:
            print(f"   ✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Specific tournament results (The Masters 2024)
    print("\n2. Testing tournament results (2024 Masters - 014)...")
    url = "https://statdata.pgatour.com/r/014/2024/leaderboard-v2.json"

    try:
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'leaderboard' in data and 'players' in data['leaderboard']:
                players = data['leaderboard']['players']
                print(f"   ✓ Success! Found {len(players)} players")
                if players:
                    player = players[0]
                    name = f"{player.get('player_bio', {}).get('first_name', '')} {player.get('player_bio', {}).get('last_name', '')}"
                    print(f"   Sample player: {name}, Position: {player.get('current_position', 'N/A')}")
            else:
                print("   ✗ No player data in response")
        else:
            print(f"   ✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Try ESPN API as backup
    print("\n3. Testing ESPN PGA API...")
    url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"

    try:
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'events' in data and len(data['events']) > 0:
                print(f"   ✓ Success! Found {len(data['events'])} current events")
                event = data['events'][0]
                print(f"   Current event: {event.get('name', 'N/A')}")
            else:
                print("   ✗ No events in response")
        else:
            print(f"   ✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 4: Historical tournament (2020 Masters)
    print("\n4. Testing historical data (2020 Masters)...")
    url = "https://statdata.pgatour.com/r/014/2020/leaderboard-v2.json"

    try:
        response = requests.get(url, timeout=10)
        print(f"   URL: {url}")
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'leaderboard' in data and 'players' in data['leaderboard']:
                print(f"   ✓ Success! Historical data available")
                print(f"   Players found: {len(data['leaderboard']['players'])}")
            else:
                print("   ✗ No player data in response")
        else:
            print(f"   ✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

if __name__ == "__main__":
    test_pga_api()
