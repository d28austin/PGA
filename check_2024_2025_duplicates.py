"""
Comprehensive duplicate check for 2024 and 2025 data
"""

import sqlite3

def check_duplicates():
    """Check for any duplicates in 2024 and 2025 data"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("COMPREHENSIVE DUPLICATE CHECK FOR 2024 AND 2025")
    print("=" * 80)

    # Check 1: Duplicates by player_id + tournament_id + year
    print("\n1. Checking for duplicate player_id + tournament_id + year...")
    cursor.execute('''
        SELECT player_id, player_name, tournament_id, year, COUNT(*) as count
        FROM tournament_results
        WHERE year IN (2024, 2025)
        AND tournament_id != 'T001'
        GROUP BY player_id, tournament_id, year
        HAVING COUNT(*) > 1
        ORDER BY count DESC, year, tournament_id, player_name
    ''')

    dupes_by_id = cursor.fetchall()
    if dupes_by_id:
        print(f"   Found {len(dupes_by_id)} duplicates:")
        for row in dupes_by_id[:20]:
            print(f"   - {row[1]} (ID: {row[0]}) | Tournament {row[2]} | Year {row[3]} | {row[4]} entries")
    else:
        print("   OK - No duplicates found")

    # Check 2: Duplicates by player_name + tournament_id + year
    print("\n2. Checking for duplicate player_name + tournament_id + year...")
    cursor.execute('''
        SELECT player_name, tournament_id, tournament_name, year, COUNT(*) as count
        FROM tournament_results
        WHERE year IN (2024, 2025)
        AND tournament_id != 'T001'
        GROUP BY player_name, tournament_id, year
        HAVING COUNT(*) > 1
        ORDER BY count DESC, year, tournament_name, player_name
    ''')

    dupes_by_name = cursor.fetchall()
    if dupes_by_name:
        print(f"   Found {len(dupes_by_name)} duplicates:")
        for row in dupes_by_name[:20]:
            print(f"   - {row[0]} | {row[2]} ({row[1]}) | Year {row[3]} | {row[4]} entries")
    else:
        print("   OK - No duplicates found")

    # Check 3: Tournament IDs appearing in multiple years
    print("\n3. Checking for tournament IDs in both 2024 and 2025...")
    cursor.execute('''
        SELECT tournament_id, tournament_name,
               COUNT(DISTINCT year) as year_count,
               GROUP_CONCAT(DISTINCT year) as years
        FROM tournament_results
        WHERE year IN (2024, 2025)
        AND tournament_id != 'T001'
        GROUP BY tournament_id
        HAVING year_count > 1
        ORDER BY tournament_name
    ''')

    cross_year = cursor.fetchall()
    if cross_year:
        print(f"   Found {len(cross_year)} tournament IDs in multiple years:")
        for row in cross_year:
            print(f"   - {row[1]} ({row[0]}) | Years: {row[3]}")
    else:
        print("   OK - No tournament IDs span multiple years")

    # Check 4: Same tournament name with different IDs in same year
    print("\n4. Checking for same tournament name with different IDs...")
    cursor.execute('''
        SELECT tournament_name, year,
               COUNT(DISTINCT tournament_id) as id_count,
               GROUP_CONCAT(DISTINCT tournament_id) as ids
        FROM tournament_results
        WHERE year IN (2024, 2025)
        AND tournament_id != 'T001'
        GROUP BY tournament_name, year
        HAVING id_count > 1
        ORDER BY year, tournament_name
    ''')

    same_name = cursor.fetchall()
    if same_name:
        print(f"   Found {len(same_name)} tournament names with multiple IDs:")
        for row in same_name:
            print(f"   - {row[0]} ({row[1]}) | {row[2]} different IDs: {row[3]}")
    else:
        print("   OK - Each tournament name has unique ID per year")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_issues = len(dupes_by_id) + len(dupes_by_name) + len(cross_year) + len(same_name)

    if total_issues == 0:
        print("ALL CHECKS PASSED - NO DUPLICATES FOUND")
        print("\n2024 and 2025 data is clean and ready to use!")
    else:
        print(f"FOUND {total_issues} ISSUES REQUIRING ATTENTION")
        print(f"  - Duplicate player/tournament combinations: {len(dupes_by_id) + len(dupes_by_name)}")
        print(f"  - Tournament IDs in multiple years: {len(cross_year)}")
        print(f"  - Tournament names with multiple IDs: {len(same_name)}")

    # Additional stats
    print("\nData Statistics:")
    for year in [2024, 2025]:
        cursor.execute('''
            SELECT COUNT(DISTINCT tournament_id), COUNT(DISTINCT tournament_name),
                   COUNT(*), COUNT(DISTINCT player_name)
            FROM tournament_results
            WHERE year = ? AND tournament_id != 'T001'
        ''', (year,))
        tid, tname, records, players = cursor.fetchone()
        print(f"  {year}: {tid} tournaments ({tname} names), {records} records, {players} unique players")

    conn.close()


if __name__ == "__main__":
    try:
        check_duplicates()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
