"""
Fetch OWGR from ESPN Athletes API
"""

import requests
import sqlite3
from datetime import datetime
import time

def fetch_all_pga_athletes():
    """Fetch all PGA Tour athletes from ESPN"""

    base_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/athletes"
    headers = {'User-Agent': 'Mozilla/5.0'}

    all_athletes = []
    page = 1
    page_size = 200

    print("Fetching PGA Tour athletes from ESPN...")

    while True:
        params = {
            'limit': page_size,
            'page': page
        }

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                break

            data = response.json()

            if 'items' not in data or not data['items']:
                break

            athletes = data['items']
            all_athletes.extend(athletes)

            print(f"  Page {page}: {len(athletes)} athletes")

            if len(athletes) < page_size:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    return all_athletes


def get_athlete_owgr(athlete_url):
    """Get OWGR for a specific athlete"""

    try:
        response = requests.get(athlete_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)

        if response.status_code != 200:
            return None, None

        data = response.json()

        name = data.get('displayName', data.get('fullName', ''))

        # Look for OWGR in various places
        owgr = None

        # Check statistics
        if 'statistics' in data:
            stats_url = data['statistics'].get('$ref')
            if stats_url:
                try:
                    stats_response = requests.get(stats_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        # Look for world ranking in stats
                        if 'splits' in stats_data:
                            for split in stats_data['splits']:
                                if 'statistics' in split:
                                    for stat in split['statistics']:
                                        if stat.get('name') in ['worldRank', 'owgr', 'worldRanking']:
                                            owgr = int(stat.get('value', 0))
                                            break
                except:
                    pass

        # Check rankings field
        if not owgr and 'rankings' in data:
            rankings_data = data['rankings']
            if isinstance(rankings_data, list):
                for ranking in rankings_data:
                    if 'value' in ranking:
                        try:
                            owgr = int(ranking['value'])
                            break
                        except:
                            pass

        return name, owgr

    except Exception as e:
        return None, None


def fetch_owgr_for_all_athletes():
    """Fetch OWGR for all PGA athletes"""

    athletes = fetch_all_pga_athletes()

    if not athletes:
        print("No athletes found")
        return {}

    print()
    print(f"Fetching OWGR for {len(athletes)} athletes...")
    print()

    rankings = {}
    found = 0
    processed = 0

    for i, athlete in enumerate(athletes, 1):
        athlete_url = athlete.get('$ref')

        if not athlete_url:
            continue

        name, owgr = get_athlete_owgr(athlete_url)

        if name and owgr and owgr > 0:
            rankings[name] = owgr
            found += 1
            if found <= 10:
                print(f"  [{i}/{len(athletes)}] {name}: #{owgr}")

        processed += 1

        if processed % 50 == 0:
            print(f"  Progress: {processed}/{len(athletes)} processed, {found} rankings found")

        time.sleep(0.2)  # Rate limiting

    return rankings


def save_owgr_to_database(rankings, db_path='data/cache/pga_data.db'):
    """Save OWGR rankings to database"""

    if not rankings:
        print("No rankings to save")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owgr_rankings (
            player_name TEXT PRIMARY KEY,
            ranking INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    timestamp = datetime.now().isoformat()

    for player_name, ranking in rankings.items():
        cursor.execute("""
            INSERT OR REPLACE INTO owgr_rankings
            (player_name, ranking, last_updated)
            VALUES (?, ?, ?)
        """, (player_name, ranking, timestamp))

    conn.commit()
    conn.close()

    print()
    print(f"[OK] Saved {len(rankings)} rankings to database")
    print(f"Last updated: {timestamp}")


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR FETCHER - ESPN ATHLETES API")
    print("=" * 80)
    print()

    rankings = fetch_owgr_for_all_athletes()

    if rankings:
        print()
        print(f"Successfully fetched {len(rankings)} OWGR rankings!")
        print()

        print("Top 15:")
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
        for player, rank in sorted_rankings[:15]:
            print(f"  #{rank}: {player}")

        if "Matthieu Pavon" in rankings:
            print()
            print(f"[OK] Matthieu Pavon: #{rankings['Matthieu Pavon']}")

        save_owgr_to_database(rankings)

    else:
        print()
        print("No rankings found via ESPN API")
        print()
        print("Alternative: Use CSV import")
        print("python import_owgr_csv.py rankings.csv")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
