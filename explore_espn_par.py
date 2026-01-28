"""
Explore ESPN API to find par data
"""

import requests
import json

base_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"

# Test with The Sentry tournament
event_id = "401580329"

# Try different endpoints
endpoints = [
    f"{base_url}/events/{event_id}",
    f"{base_url}/events/{event_id}/competitions/{event_id}",
    f"{base_url}/events/{event_id}/competitions/{event_id}/competitors",
    f"{base_url}/events/{event_id}/competitions/{event_id}/situation",
]

for endpoint in endpoints:
    print("=" * 80)
    print(f"Testing: {endpoint}")
    print("=" * 80)

    try:
        response = requests.get(endpoint, timeout=10)
        if response.status_code == 200:
            data = response.json()

            # Look for par-related keys
            def find_par_keys(obj, path=""):
                """Recursively search for keys containing 'par'"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if 'par' in key.lower():
                            print(f"Found key '{key}' at {path}.{key}: {value}")
                        if isinstance(value, (dict, list)):
                            find_par_keys(value, f"{path}.{key}")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:3]):  # Only check first 3 items
                        find_par_keys(item, f"{path}[{i}]")

            find_par_keys(data)

            # Also print some key structure
            if isinstance(data, dict):
                print(f"\nTop-level keys: {list(data.keys())[:20]}")

            print()
        else:
            print(f"Status code: {response.status_code}")
            print()
    except Exception as e:
        print(f"Error: {e}")
        print()
