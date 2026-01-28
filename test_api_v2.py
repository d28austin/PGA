"""
Test alternative PGA data sources
"""

import requests
import json

def test_espn_api():
    """Test ESPN PGA API"""
    print("Testing ESPN PGA API...")

    # Test scoreboard
    url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success! Response keys: {list(data.keys())}")

            if 'events' in data:
                print(f"Found {len(data['events'])} events")
                if data['events']:
                    event = data['events'][0]
                    print(f"Sample event: {event.get('name', 'N/A')}")
                    print(f"Event ID: {event.get('id', 'N/A')}")
        else:
            print(f"Failed with status {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def test_datagolf_api():
    """Test Data Golf API (free tier)"""
    print("\nTesting Data Golf API...")

    url = "https://feeds.datagolf.com/preds/in-play?tour=pga"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Success! Data Golf API accessible")
            print(f"Response type: {type(data)}")
        elif response.status_code == 403:
            print("API key required for Data Golf")
        else:
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

def test_sportsdata_io():
    """Test SportsData.io"""
    print("\nTesting SportsData.io...")

    # This requires an API key, but let's test connectivity
    url = "https://api.sportsdata.io/golf/v2/json/Tournaments/2024"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 401:
            print("API accessible but requires key")
        elif response.status_code == 200:
            print("Success! API accessible")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_espn_api()
    test_datagolf_api()
    test_sportsdata_io()
