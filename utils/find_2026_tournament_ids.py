"""
Find 2026 tournament IDs from ESPN and update database
"""

import requests
import sqlite3
from pathlib import Path

def fetch_2026_tournaments():
    """Fetch all 2026 PGA Tour tournaments from ESPN"""

    try:
        # ESPN scoreboard API for 2026
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
        params = {'dates': 2026}
        headers = {'User-Agent': 'Mozilla/5.0'}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"Failed to fetch: status {response.status_code}")
            return []

        data = response.json()

        if 'events' not in data:
            print("No events found")
            return []

        tournaments = []
        for event in data['events']:
            tournament = {
                'id': event.get('id'),
                'name': event.get('name'),
                'date': event.get('date'),
                'status': event.get('status', {}).get('type', {}).get('description', '')
            }
            tournaments.append(tournament)

        return tournaments

    except Exception as e:
        print(f"Error: {e}")
        return []


def save_2026_tournament_ids(db_path='data/cache/pga_data.db'):
    """Save 2026 tournament IDs to database"""

    tournaments = fetch_2026_tournaments()

    if not tournaments:
        print("No tournaments found")
        return

    print(f"Found {len(tournaments)} tournaments for 2026")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a mapping table for 2026 tournament IDs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_2026_ids (
            tournament_name TEXT PRIMARY KEY,
            tournament_id TEXT NOT NULL,
            date TEXT,
            status TEXT
        )
    """)

    added = 0
    updated = 0

    for tournament in tournaments:
        name = tournament['name']
        tid = tournament['id']

        print(f"  {name}")
        print(f"    ID: {tid}")
        print(f"    Date: {tournament['date']}")
        print(f"    Status: {tournament['status']}")
        print()

        # Insert or update
        cursor.execute("""
            INSERT OR REPLACE INTO tournament_2026_ids
            (tournament_name, tournament_id, date, status)
            VALUES (?, ?, ?, ?)
        """, (name, tid, tournament['date'], tournament['status']))

        if cursor.rowcount > 0:
            added += 1

    conn.commit()
    conn.close()

    print(f"Saved {added} tournament IDs to database")


if __name__ == "__main__":
    print("=" * 80)
    print("FETCHING 2026 PGA TOUR TOURNAMENT IDs")
    print("=" * 80)
    print()

    save_2026_tournament_ids()

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
