"""
Fetch OWGR rankings from ESPN player data
ESPN includes OWGR in their player statistics
"""

import requests
import sqlite3
from datetime import datetime
import time

def get_all_pga_players_from_db(db_path='data/cache/pga_data.db'):
    """Get list of all unique players from tournament results"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT player_name
        FROM tournament_results
        WHERE player_name IS NOT NULL
        AND player_name != ''
        ORDER BY player_name
    """)

    players = [row[0] for row in cursor.fetchall()]
    conn.close()

    return players


def fetch_owgr_from_espn_leaderboard():
    """
    Fetch OWGR from ESPN's recent tournament leaderboard
    This gives us current rankings for active players
    """

    rankings = {}

    # Use a recent 2026 tournament that has started
    tournament_ids = [
        '401811928',  # Sony Open 2026
        '401811929',  # American Express 2026
        '401811930',  # Farmers Insurance Open 2026
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print("Fetching OWGR from ESPN tournament leaderboards...")
    print()

    for tid in tournament_ids:
        print(f"Tournament {tid}...", end=' ', flush=True)

        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
            params = {
                'league': 'pga',
                'event': tid
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"Failed (status {response.status_code})")
                continue

            data = response.json()

            if 'events' not in data or len(data['events']) == 0:
                print("No events")
                continue

            event = data['events'][0]

            if 'competitions' not in event or len(event['competitions']) == 0:
                print("No competitions")
                continue

            competition = event['competitions'][0]

            if 'competitors' not in competition:
                print("No competitors")
                continue

            competitors = competition['competitors']

            found = 0
            for competitor in competitors:
                if 'athlete' not in competitor:
                    continue

                athlete = competitor['athlete']
                player_name = athlete.get('displayName')

                if not player_name:
                    continue

                # Check for OWGR in statistics
                statistics = competitor.get('statistics', [])

                for stat in statistics:
                    stat_name = stat.get('name', '')

                    # ESPN uses different names for OWGR
                    if stat_name in ['worldRank', 'owgr', 'worldRanking']:
                        try:
                            rank = int(stat.get('value', 0))
                            if rank > 0:
                                # Only update if we don't have this player or this is a better (lower) rank
                                if player_name not in rankings or rank < rankings[player_name]:
                                    rankings[player_name] = rank
                                    found += 1
                        except:
                            pass

            print(f"OK ({found} new rankings)")

            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            continue

    return rankings


def save_owgr_to_database(rankings, db_path='data/cache/pga_data.db'):
    """Save OWGR rankings to database"""

    if not rankings:
        print("No rankings to save")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create OWGR table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owgr_rankings (
            player_name TEXT PRIMARY KEY,
            ranking INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    # Update timestamp
    timestamp = datetime.now().isoformat()

    # Insert/update rankings
    updated = 0
    for player_name, ranking in rankings.items():
        cursor.execute("""
            INSERT OR REPLACE INTO owgr_rankings
            (player_name, ranking, last_updated)
            VALUES (?, ?, ?)
        """, (player_name, ranking, timestamp))
        updated += 1

    conn.commit()
    conn.close()

    print(f"Saved {updated} rankings to database")
    print(f"Last updated: {timestamp}")


def import_owgr_from_csv(csv_path):
    """
    Import OWGR from a CSV file
    Expected format: player_name,ranking
    """

    import csv

    rankings = {}

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header

            for row in reader:
                if len(row) >= 2:
                    player_name = row[0].strip()
                    try:
                        ranking = int(row[1])
                        rankings[player_name] = ranking
                    except:
                        pass

        return rankings

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return {}


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR RANKINGS FETCHER (ESPN)")
    print("=" * 80)
    print()

    # Fetch from ESPN
    rankings = fetch_owgr_from_espn_leaderboard()

    if rankings:
        print()
        print(f"Found {len(rankings)} players with OWGR rankings")
        print()

        print("Sample rankings:")
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
        for player, rank in sorted_rankings[:15]:
            print(f"  #{rank}: {player}")

        print()
        print("=" * 80)
        print("SAVING TO DATABASE")
        print("=" * 80)
        print()

        save_owgr_to_database(rankings)

        # Check Matthieu Pavon
        if "Matthieu Pavon" in rankings:
            print()
            print(f"✅ Matthieu Pavon: Ranked #{rankings['Matthieu Pavon']}")
        else:
            print()
            print(f"❌ Matthieu Pavon: Not found in ESPN data")

    else:
        print()
        print("No rankings found from ESPN")
        print()
        print("Alternative: You can manually download OWGR rankings CSV from:")
        print("  https://www.owgr.com/ranking")
        print()
        print("Then run:")
        print("  python fetch_owgr_from_espn.py import rankings.csv")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
