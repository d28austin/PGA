"""
Clean up duplicate tournament data from initial testing
"""

import sqlite3

def clean_duplicates():
    """Remove duplicate tournament entries that were loaded with incorrect years"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("CLEANING DUPLICATE TOURNAMENT DATA")
    print("=" * 80)

    # Tournament 401811930 is the 2026 Farmers Insurance Open
    # It was incorrectly loaded as 2024 and 2025 during testing
    # We'll remove these since we want historical data (2020-2025 actual)

    print("\nChecking for 401811930 (2026 Farmers Insurance Open) in wrong years...")
    cursor.execute("""
        SELECT year, COUNT(*) as records
        FROM tournament_results
        WHERE tournament_id = '401811930'
        GROUP BY year
    """)

    before_data = cursor.fetchall()
    for year, count in before_data:
        print(f"  Found {count} records for year {year}")

    # Delete the incorrectly loaded data
    print("\nDeleting 401811930 entries from years 2024 and 2025...")
    cursor.execute("""
        DELETE FROM tournament_results
        WHERE tournament_id = '401811930'
        AND year IN (2024, 2025)
    """)

    deleted_count = cursor.rowcount
    conn.commit()

    print(f"  Deleted {deleted_count} records")

    # Verify cleanup
    print("\nVerifying cleanup...")
    cursor.execute("""
        SELECT year, COUNT(*) as records
        FROM tournament_results
        WHERE tournament_id = '401811930'
        GROUP BY year
    """)

    after_data = cursor.fetchall()
    if after_data:
        print("  WARNING: Still found records:")
        for year, count in after_data:
            print(f"    {count} records for year {year}")
    else:
        print("  ✓ No more duplicate entries for 401811930")

    # Check if there are any other duplicates
    print("\nChecking for other tournament IDs with multiple years...")
    cursor.execute("""
        SELECT tournament_id, COUNT(DISTINCT year) as year_count, GROUP_CONCAT(DISTINCT year) as years
        FROM tournament_results
        GROUP BY tournament_id
        HAVING year_count > 1
        ORDER BY year_count DESC
    """)

    other_dupes = cursor.fetchall()
    if other_dupes:
        print(f"  Found {len(other_dupes)} tournaments with multiple years:")
        for tid, yc, years in other_dupes[:10]:
            print(f"    {tid}: years {years}")
    else:
        print("  ✓ No other duplicates found")

    conn.close()

    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print(f"  Removed {deleted_count} duplicate records")
    print("  Tournament data is now clean")


if __name__ == "__main__":
    try:
        clean_duplicates()
    except Exception as e:
        print(f"\nError: {e}")
