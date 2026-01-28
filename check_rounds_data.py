"""
Check if ESPN API provides round information
"""

import requests
import json

event_id = "401580333"  # AT&T Pebble Beach (3 rounds)
base_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"

endpoint = f"{base_url}/events/{event_id}"
response = requests.get(endpoint, timeout=10)

if response.status_code == 200:
    data = response.json()

    print("Looking for round information in the API response...")
    print("\n" + "=" * 80)

    # Check for rounds in various places
    if 'competitions' in data:
        print("competitions:", json.dumps(data['competitions'], indent=2)[:500])

    # Look for any key containing 'round'
    def find_round_keys(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if 'round' in key.lower():
                    print(f"\nFound '{key}' at {path}: {value}")
                if isinstance(value, (dict, list)) and path.count('.') < 3:  # Limit depth
                    find_round_keys(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:2]):
                find_round_keys(item, f"{path}[{i}]")

    find_round_keys(data)

    # Check competition endpoint
    print("\n" + "=" * 80)
    print("Checking competition endpoint...")
    comp_endpoint = f"{base_url}/events/{event_id}/competitions/{event_id}"
    comp_response = requests.get(comp_endpoint, timeout=10)
    if comp_response.status_code == 200:
        comp_data = comp_response.json()
        print("Top-level keys:", list(comp_data.keys())[:20])

        if 'format' in comp_data:
            print(f"\nformat: {comp_data['format']}")

        find_round_keys(comp_data, "competition")
