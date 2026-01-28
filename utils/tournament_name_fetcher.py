"""
Fetch tournament names from ESPN API for any tournament ID
"""

import requests
import sqlite3
from typing import Dict, Optional
import time


def get_tournament_name_from_api(event_id: str) -> Optional[str]:
    """
    Fetch tournament name from ESPN API

    Args:
        event_id: ESPN tournament/event ID

    Returns: Tournament name or None
    """
    try:
        url = f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{event_id}"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        if response.status_code == 200:
            data = response.json()
            name = data.get('name') or data.get('shortName')
            return name
        return None
    except Exception as e:
        print(f"Error fetching name for {event_id}: {e}")
        return None


def build_tournament_name_cache(db_path: str = 'data/cache/pga_data.db') -> Dict[str, str]:
    """
    Build a cache of tournament_id -> name mappings for all tournaments in database

    Args:
        db_path: Path to SQLite database

    Returns: Dict mapping tournament_id to tournament_name
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all unique tournament IDs
    cursor.execute("""
        SELECT DISTINCT tournament_id
        FROM tournament_results
        WHERE tournament_id != 'T001'
        ORDER BY tournament_id
    """)

    tournament_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"Fetching names for {len(tournament_ids)} unique tournaments...")

    name_cache = {}
    for i, tid in enumerate(tournament_ids, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(tournament_ids)}")

        name = get_tournament_name_from_api(tid)
        if name:
            name_cache[tid] = name
        else:
            name_cache[tid] = tid  # Fallback to ID

        # Rate limiting
        time.sleep(0.2)

    print(f"Completed: {len(name_cache)} tournament names fetched")
    return name_cache


def get_tournaments_by_name(db_path: str = 'data/cache/pga_data.db') -> Dict[str, list]:
    """
    Get all tournament IDs grouped by their display name

    Returns: Dict mapping tournament_name -> list of (tournament_id, year) tuples
    """
    cache = build_tournament_name_cache(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tournament_id, year combinations
    cursor.execute("""
        SELECT DISTINCT tournament_id, year
        FROM tournament_results
        WHERE tournament_id != 'T001'
        ORDER BY tournament_id, year
    """)

    tournament_year_pairs = cursor.fetchall()
    conn.close()

    # Group by tournament name
    by_name = {}
    for tid, year in tournament_year_pairs:
        name = cache.get(tid, tid)
        if name not in by_name:
            by_name[name] = []
        by_name[name].append((tid, year))

    return by_name


if __name__ == "__main__":
    # Test
    print("Building tournament name cache...")
    tournaments = get_tournaments_by_name()

    print(f"\nFound {len(tournaments)} unique tournament names:")
    for name, id_year_pairs in sorted(tournaments.items())[:10]:
        years = [year for _, year in id_year_pairs]
        print(f"  {name}: {len(id_year_pairs)} years ({min(years)}-{max(years)})")
