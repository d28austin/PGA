"""
Find and fix tournament names that are slightly different but refer to the same tournament
"""

import sqlite3
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_similar_names():
    """Find tournament names that are similar and should be aggregated"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Get all unique tournament names
    cursor.execute('''
        SELECT DISTINCT tournament_name, COUNT(DISTINCT year) as years,
               MIN(year) as first, MAX(year) as last,
               COUNT(*) as records
        FROM tournament_results
        WHERE tournament_name IS NOT NULL AND tournament_id != 'T001'
        GROUP BY tournament_name
        ORDER BY tournament_name
    ''')

    names = cursor.fetchall()

    print("=" * 80)
    print(f"FOUND {len(names)} UNIQUE TOURNAMENT NAMES")
    print("=" * 80)
    print()

    # Print all names first
    for name, years, first, last, records in names:
        year_range = f"{first}-{last}" if years > 1 else str(first)
        print(f"{name:60} | {years:2} years ({year_range:9}) | {records:4} records")

    print()
    print("=" * 80)
    print("FINDING SIMILAR NAMES")
    print("=" * 80)
    print()

    # Find similar names
    similar_groups = []
    checked = set()

    for i, (name1, years1, first1, last1, records1) in enumerate(names):
        if name1 in checked:
            continue

        similar_to_name1 = [(name1, years1, first1, last1, records1)]

        for j, (name2, years2, first2, last2, records2) in enumerate(names):
            if i != j and name2 not in checked:
                # Check similarity
                sim = similarity(name1, name2)

                # High similarity or obvious matches
                if sim > 0.85:
                    similar_to_name1.append((name2, years2, first2, last2, records2))
                    checked.add(name2)
                # Check for year prefix pattern (e.g., "2020 Masters" vs "Masters")
                elif name1.replace("2020 ", "") == name2 or name1.replace("2021 ", "") == name2:
                    similar_to_name1.append((name2, years2, first2, last2, records2))
                    checked.add(name2)
                elif name2.replace("2020 ", "") == name1 or name2.replace("2021 ", "") == name1:
                    similar_to_name1.append((name2, years2, first2, last2, records2))
                    checked.add(name2)

        if len(similar_to_name1) > 1:
            similar_groups.append(similar_to_name1)
            checked.add(name1)

    if similar_groups:
        print(f"Found {len(similar_groups)} groups of similar names:\n")

        for group_num, group in enumerate(similar_groups, 1):
            print(f"Group {group_num}:")
            for name, years, first, last, records in group:
                year_range = f"{first}-{last}" if years > 1 else str(first)
                print(f"  - {name:60} | {years} years ({year_range:9}) | {records} records")
            print()
    else:
        print("No obvious similar names found automatically.")

    # Manual patterns to check
    print("=" * 80)
    print("CHECKING COMMON PATTERNS")
    print("=" * 80)
    print()

    patterns = [
        "Masters",
        "U.S. Open",
        "PGA Championship",
        "Open Championship",
        "The Open",
        "Players",
        "Arnold Palmer",
        "Memorial",
        "Genesis",
        "Sentry",
        "Sony Open",
        "American Express",
        "Farmers Insurance",
        "Pebble Beach",
        "Phoenix",
        "Honda",
        "Bay Hill",
        "Wells Fargo",
        "Byron Nelson",
        "Colonial",
        "Memorial",
        "RBC Heritage",
        "Travelers",
        "John Deere",
        "Barracuda",
        "Wyndham",
        "Mexico",
        "Mexican",
    ]

    for pattern in patterns:
        matches = [name for name, _, _, _, _ in names if pattern.lower() in name.lower()]
        if len(matches) > 1:
            print(f"\nContains '{pattern}':")
            for match in matches:
                print(f"  - {match}")

    conn.close()


if __name__ == "__main__":
    try:
        find_similar_names()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
