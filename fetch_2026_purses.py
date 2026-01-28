"""
Fetch purse information for all 2026 tournaments and save to database
"""

import sqlite3
import requests
import time
import re


def fetch_tournament_purse(tournament_id):
    """Fetch tournament purse from ESPN API"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
        params = {'league': 'pga', 'event': tournament_id}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Try to find purse in various locations
            if 'event' in data:
                event = data['event']

                # Check purse field
                if 'purse' in event:
                    return event['purse']

                # Check competitions
                if 'competitions' in event and len(event['competitions']) > 0:
                    comp = event['competitions'][0]
                    if 'purse' in comp:
                        return comp['purse']

                    # Check notes for purse information
                    if 'notes' in comp:
                        for note in comp['notes']:
                            if isinstance(note, dict) and 'headline' in note:
                                if 'purse' in note['headline'].lower():
                                    # Try to extract number from text
                                    match = re.search(r'\$?([\d,]+)', note['headline'])
                                    if match:
                                        return int(match.group(1).replace(',', ''))

        return None
    except Exception as e:
        print(f"Error fetching purse: {e}")
        return None


def fetch_all_purses():
    """Fetch purse data for all 2026 tournaments"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Add purse column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE tournament_2026_ids ADD COLUMN purse INTEGER DEFAULT 0")
        conn.commit()
        print("Added purse column to database")
    except:
        print("Purse column already exists")

    # Get all tournaments
    cursor.execute("SELECT tournament_name, tournament_id FROM tournament_2026_ids ORDER BY date")
    tournaments = cursor.fetchall()

    print(f"Fetching purse data for {len(tournaments)} tournaments...")
    print()

    fetched = 0
    failed = 0

    for i, (name, tournament_id) in enumerate(tournaments, 1):
        print(f"[{i}/{len(tournaments)}] {name}...", end=" ")

        purse = fetch_tournament_purse(tournament_id)

        if purse and purse > 0:
            cursor.execute("""
                UPDATE tournament_2026_ids
                SET purse = ?
                WHERE tournament_id = ?
            """, (purse, tournament_id))
            print(f"${purse:,.0f}")
            fetched += 1
        else:
            print("Not available")
            failed += 1

        conn.commit()
        time.sleep(0.3)  # Rate limiting

    conn.close()

    print()
    print("=" * 80)
    print(f"COMPLETE: {fetched} purses fetched, {failed} not available")
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("FETCHING 2026 TOURNAMENT PURSES")
    print("=" * 80)
    print()

    fetch_all_purses()
