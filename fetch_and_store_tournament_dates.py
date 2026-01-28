"""
Fetch tournament dates from ESPN and update database
This script scrapes tournament dates from ESPN API and stores them in the database
for reference by tournament name and year
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from data.espn_fetcher import ESPNPGAFetcher
import sqlite3
import time
from datetime import datetime


def update_tournaments_table_schema(db_path: str):
    """Add end_date column to tournaments table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if end_date column exists
        cursor.execute("PRAGMA table_info(tournaments)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'end_date' not in columns:
            print("Adding end_date column to tournaments table...")
            cursor.execute("ALTER TABLE tournaments ADD COLUMN end_date TEXT")
            conn.commit()
            print("[OK] Added end_date column")
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()


def fetch_and_store_tournament_dates(years: list = None, db_path: str = "data/cache/pga_data.db"):
    """
    Fetch tournament dates from ESPN and store in database

    Args:
        years: List of years to fetch (defaults to 2020-2026)
        db_path: Path to SQLite database
    """
    if years is None:
        years = list(range(2020, 2027))  # 2020-2026

    # First update the schema to add end_date if needed
    update_tournaments_table_schema(db_path)

    fetcher = ESPNPGAFetcher()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total_updated = 0
    total_new = 0

    for year in years:
        print(f"\n{'='*60}")
        print(f"Fetching tournaments for {year}...")
        print(f"{'='*60}")

        # Get calendar from ESPN
        calendar = fetcher.get_season_calendar(year)

        if not calendar:
            print(f"No tournaments found for {year}")
            continue

        print(f"Found {len(calendar)} tournaments for {year}")

        for tournament in calendar:
            event_id = tournament.get('event_id')
            name = tournament.get('name', 'Unknown')
            start_date = tournament.get('start_date')
            end_date = tournament.get('end_date')

            if not event_id or not name:
                continue

            # Create composite ID for this year's tournament
            composite_id = f"{event_id}_{year}"

            # Check if tournament already exists
            cursor.execute("""
                SELECT tournament_id, tournament_name, start_date, end_date
                FROM tournaments
                WHERE tournament_id = ?
            """, (composite_id,))

            existing = cursor.fetchone()

            if existing:
                # Update existing tournament
                old_start = existing[2]
                old_end = existing[3]

                if old_start != start_date or old_end != end_date:
                    cursor.execute("""
                        UPDATE tournaments
                        SET tournament_name = ?, start_date = ?, end_date = ?, last_updated = ?
                        WHERE tournament_id = ?
                    """, (name, start_date, end_date, datetime.now(), composite_id))

                    print(f"[UPDATED] {name} ({year})")
                    print(f"  Start: {start_date}, End: {end_date}")
                    total_updated += 1
                else:
                    print(f"  [SKIPPED] {name} ({year}) - already up to date")
            else:
                # Insert new tournament using INSERT OR REPLACE to avoid duplicates
                cursor.execute("""
                    INSERT OR REPLACE INTO tournaments
                    (tournament_id, tournament_name, year, start_date, end_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (composite_id, name, year, start_date, end_date, datetime.now()))

                print(f"[ADDED] {name} ({year})")
                print(f"  Start: {start_date}, End: {end_date}")
                total_new += 1

            # Commit after each tournament to avoid losing progress
            conn.commit()

        # Rate limiting between years
        time.sleep(1)

    conn.close()

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  New tournaments added: {total_new}")
    print(f"  Existing tournaments updated: {total_updated}")
    print(f"  Total processed: {total_new + total_updated}")
    print(f"{'='*60}\n")


def verify_tournament_dates(db_path: str = "data/cache/pga_data.db"):
    """Verify that tournament dates were stored correctly"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get sample of tournaments with dates
    cursor.execute("""
        SELECT tournament_name, year, start_date, end_date
        FROM tournaments
        WHERE start_date IS NOT NULL
        ORDER BY year DESC, start_date DESC
        LIMIT 10
    """)

    results = cursor.fetchall()

    print("\nSample of tournaments with dates:")
    print(f"{'='*80}")
    for row in results:
        print(f"{row[0][:40]:40} | {row[1]} | {row[2]} to {row[3]}")

    # Count tournaments with dates
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(start_date) as with_start_date,
            COUNT(end_date) as with_end_date
        FROM tournaments
    """)

    stats = cursor.fetchone()
    print(f"\n{'='*80}")
    print(f"Database Statistics:")
    print(f"  Total tournaments: {stats[0]}")
    print(f"  With start_date: {stats[1]}")
    print(f"  With end_date: {stats[2]}")
    print(f"{'='*80}\n")

    conn.close()


if __name__ == "__main__":
    print("PGA Tournament Date Fetcher")
    print("="*60)
    print("This script fetches tournament dates from ESPN and updates")
    print("the database for accurate date displays throughout the app.")
    print("="*60)

    # Fetch and store tournament dates for recent years
    fetch_and_store_tournament_dates(years=[2020, 2021, 2022, 2023, 2024, 2025, 2026])

    # Verify the data was stored
    verify_tournament_dates()

    print("\n[SUCCESS] Tournament dates have been updated in the database")
    print("  The Recent Form tab will now show actual tournament dates")
    print("  instead of estimated dates.\n")
