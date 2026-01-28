"""
Fetch venue/course data to find par
"""

import requests
import json

# Fetch venue data
venue_url = "http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/venues/1"

print("Fetching venue data...")
print(f"URL: {venue_url}")

try:
    response = requests.get(venue_url, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        # Save to file
        with open('venue_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("Saved to venue_data.json")

        print(f"\nVenue keys: {list(data.keys())}")

        # Look for useful info
        for key in ['name', 'grass', 'par', 'yardage', 'course', 'courses']:
            if key in data:
                print(f"{key}: {data[key]}")

        # Check if there's a courses field
        if 'courses' in data or 'course' in data:
            print("\nFound course data!")
            import pprint
            pprint.pprint(data.get('courses') or data.get('course'))

except Exception as e:
    print(f"Error: {e}")
