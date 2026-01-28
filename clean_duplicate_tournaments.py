"""
Clean duplicate tournament entries from the database
"""

import sqlite3
from datetime import datetime


def clean_duplicate_tournaments(db_path: str = "data/cache/pga_data.db"):
    """Remove duplicate tournament entries, keeping only the most recent one"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Cleaning duplicate tournament entries...")
    print("="*60)

    # Find all duplicate tournament_ids
    cursor.execute("""
        SELECT tournament_id, COUNT(*) as count
        FROM tournaments
        GROUP BY tournament_id
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()
    print(f"Found {len(duplicates)} tournament_ids with duplicates")

    total_deleted = 0

    for tournament_id, count in duplicates:
        # Keep only the most recent entry for each tournament_id
        cursor.execute("""
            DELETE FROM tournaments
            WHERE rowid NOT IN (
                SELECT MAX(rowid)
                FROM tournaments
                WHERE tournament_id = ?
            )
            AND tournament_id = ?
        """, (tournament_id, tournament_id))

        deleted = cursor.rowcount
        total_deleted += deleted

        if deleted > 0:
            print(f"Cleaned {tournament_id}: removed {deleted} duplicate(s)")

    conn.commit()

    # Verify no duplicates remain
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT tournament_id, COUNT(*) as count
            FROM tournaments
            GROUP BY tournament_id
            HAVING COUNT(*) > 1
        )
    """)

    remaining_duplicates = cursor.fetchone()[0]

    print("="*60)
    print(f"Summary:")
    print(f"  Total duplicate entries removed: {total_deleted}")
    print(f"  Remaining duplicates: {remaining_duplicates}")
    print("="*60)

    # Show tournament stats
    cursor.execute("SELECT COUNT(*) FROM tournaments")
    total_tournaments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tournaments WHERE start_date IS NOT NULL")
    with_dates = cursor.fetchone()[0]

    print(f"\nFinal Statistics:")
    print(f"  Total tournaments: {total_tournaments}")
    print(f"  Tournaments with dates: {with_dates}")
    print(f"  Coverage: {with_dates/total_tournaments*100:.2f}%")

    conn.close()

    return total_deleted


if __name__ == "__main__":
    deleted_count = clean_duplicate_tournaments()

    if deleted_count > 0:
        print(f"\n[SUCCESS] Cleaned {deleted_count} duplicate tournament entries")
        print("The Quick Player Analysis Recent Form tab should no longer show duplicates.")
    else:
        print("\n[INFO] No duplicates found - database is clean")
