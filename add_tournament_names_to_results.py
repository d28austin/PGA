"""
Add tournament_name column to tournament_results and populate it
"""

import sqlite3
import requests
import time


def get_tournament_name_from_api(event_id: str) -> str:
    """Fetch tournament name from ESPN API"""
    try:
        url = f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        if response.status_code == 200:
            data = response.json()
            return data.get('name') or data.get('shortName') or event_id
        return event_id
    except Exception:
        return event_id


def add_and_populate_tournament_names():
    """Add tournament_name column and populate it"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(tournament_results)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'tournament_name' not in columns:
        print("Adding tournament_name column...")
        cursor.execute("ALTER TABLE tournament_results ADD COLUMN tournament_name TEXT")
        conn.commit()

    # Get all unique tournament IDs that need names
    cursor.execute("""
        SELECT DISTINCT tournament_id
        FROM tournament_results
        WHERE tournament_name IS NULL AND tournament_id != 'T001'
        ORDER BY tournament_id
    """)

    tournament_ids = [row[0] for row in cursor.fetchall()]

    print(f"=" * 80)
    print(f"POPULATING TOURNAMENT NAMES FOR {len(tournament_ids)} TOURNAMENTS")
    print(f"=" * 80)

    name_cache = {}
    for i, tid in enumerate(tournament_ids, 1):
        print(f"\n[{i}/{len(tournament_ids)}] {tid}...", end='', flush=True)

        # Fetch name from API
        name = get_tournament_name_from_api(tid)
        name_cache[tid] = name

        # Update all rows with this tournament_id
        cursor.execute("""
            UPDATE tournament_results
            SET tournament_name = ?
            WHERE tournament_id = ?
        """, (name, tid))

        conn.commit()
        print(f" {name}")

        # Rate limiting
        time.sleep(0.2)

    conn.close()

    print("\n" + "=" * 80)
    print(f"COMPLETE: {len(name_cache)} tournament names populated")
    print("=" * 80)

    # Print summary
    print("\nUnique tournaments:")
    unique_names = set(name_cache.values())
    for name in sorted(unique_names)[:20]:
        print(f"  - {name}")
    if len(unique_names) > 20:
        print(f"  ... and {len(unique_names) - 20} more")


if __name__ == "__main__":
    try:
        add_and_populate_tournament_names()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
