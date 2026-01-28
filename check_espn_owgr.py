"""
Check if ESPN API provides OWGR data
"""

import requests
import json

base_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"

# Test with a known player - let's try Scottie Scheffler
print("=" * 80)
print("CHECKING ESPN API FOR OWGR DATA")
print("=" * 80)

# First, get a competitor from a recent event
event_id = "401580329"  # The Sentry 2024
comp_url = f"{base_url}/events/{event_id}/competitions/{event_id}"

response = requests.get(comp_url, timeout=10)
if response.status_code == 200:
    data = response.json()

    if 'competitors' in data and data['competitors']:
        # Get first competitor
        first_comp_ref = data['competitors'][0]['$ref']
        print(f"\nFetching competitor details from:")
        print(f"  {first_comp_ref}")

        comp_resp = requests.get(first_comp_ref, timeout=10)
        if comp_resp.status_code == 200:
            comp_data = comp_resp.json()

            print(f"\nCompetitor keys: {list(comp_data.keys())}")

            # Get athlete info
            if 'athlete' in comp_data and '$ref' in comp_data['athlete']:
                athlete_url = comp_data['athlete']['$ref']
                print(f"\nFetching athlete from: {athlete_url}")

                athlete_resp = requests.get(athlete_url, timeout=10)
                if athlete_resp.status_code == 200:
                    athlete_data = athlete_resp.json()

                    player_name = athlete_data.get('displayName', 'Unknown')
                    print(f"\nPlayer: {player_name}")
                    print(f"\nAthlete data keys: {list(athlete_data.keys())}")

                    # Look for ranking/OWGR data
                    for key in athlete_data.keys():
                        if 'rank' in key.lower() or 'rating' in key.lower() or 'world' in key.lower():
                            print(f"\n  Found: {key} = {athlete_data[key]}")

                    # Check if there's a statistics or rankings link
                    if 'statistics' in athlete_data:
                        print(f"\n  Statistics: {athlete_data['statistics']}")

                    if 'rankings' in athlete_data:
                        print(f"\n  Rankings: {athlete_data['rankings']}")

print("\n" + "=" * 80)
print("ESPN API does not appear to include OWGR data directly")
print("We'll need to use an alternative approach")
print("=" * 80)
