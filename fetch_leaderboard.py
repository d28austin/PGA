
"""
Fetch tournament leaderboard data from ESPN
"""

import requests
import json

def fetch_tournament_leaderboard(event_id):
    """Fetch leaderboard for a specific event"""
    print(f"Fetching leaderboard for event {event_id}...")

    # Try the competition endpoint
    url = f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}/competitions/{event_id}"

    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Keys: {list(data.keys())[:15]}")

            # Save full response
            with open(f'competition_{event_id}.json', 'w') as f:
                json.dump(data, f, indent=2)

            # Check for competitors/players
            if 'competitors' in data:
                competitors_ref = data['competitors']
                print(f"\nCompetitors reference: {competitors_ref}")

                # Fetch competitors
                if '$ref' in competitors_ref:
                    comp_url = competitors_ref['$ref']
                    comp_resp = requests.get(comp_url, timeout=10)

                    if comp_resp.status_code == 200:
                        comp_data = comp_resp.json()
                        print(f"\nCompetitors data keys: {list(comp_data.keys())}")

                        if 'items' in comp_data:
                            players = comp_data['items']
                            print(f"Found {len(players)} players")

                            # Save players data
                            with open(f'players_{event_id}.json', 'w') as f:
                                json.dump(comp_data, f, indent=2)

                            # Print sample player
                            if players:
                                player = players[0]
                                print(f"\nSample player structure:")
                                print(f"  Keys: {list(player.keys())}")

                                # Fetch full player details
                                if '$ref' in player:
                                    player_url = player['$ref']
                                    player_resp = requests.get(player_url, timeout=10)

                                    if player_resp.status_code == 200:
                                        player_detail = player_resp.json()
                                        print(f"  Full player keys: {list(player_detail.keys())[:10]}")

                                        # Save sample player
                                        with open(f'sample_player_{event_id}.json', 'w') as f:
                                            json.dump(player_detail, f, indent=2)

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Try a completed 2024 tournament
    # The Sentry 2024
    event_id = "401580329"

    fetch_tournament_leaderboard(event_id)
