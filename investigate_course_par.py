"""
Investigate if we can get actual course par from ESPN API
"""

import requests
import json

# Try to get course/par info from a known tournament
event_id = "401580329"  # The Sentry 2024

print("=" * 80)
print("INVESTIGATING COURSE PAR DATA FROM ESPN API")
print("=" * 80)

# Try different ESPN API endpoints
endpoints = [
    f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}",
    f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}/competitions/{event_id}",
    f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/summary?event={event_id}",
]

for url in endpoints:
    print(f"\n{'=' * 80}")
    print(f"Trying: {url}")
    print("=" * 80)

    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Save to file for inspection
            filename = f"course_data_{endpoints.index(url)}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved to {filename}")

            # Look for par-related fields
            data_str = json.dumps(data)
            if 'par' in data_str.lower():
                print("✓ Found 'par' in response!")
                # Try to find it
                if isinstance(data, dict):
                    for key in data.keys():
                        if 'par' in key.lower():
                            print(f"  Key with 'par': {key} = {data[key]}")
            else:
                print("✗ No 'par' found in response")

            if 'course' in data_str.lower():
                print("✓ Found 'course' in response!")
                if isinstance(data, dict):
                    for key in data.keys():
                        if 'course' in key.lower():
                            print(f"  Key with 'course': {key}")

            # Check top-level keys
            if isinstance(data, dict):
                print(f"\nTop-level keys: {list(data.keys())[:10]}")

    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 80)
print("Investigation complete - check the JSON files for details")
print("=" * 80)
