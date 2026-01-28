"""
Import OWGR rankings from CSV file

Instructions:
1. Go to https://www.owgr.com/ranking
2. Scroll down and click "Download" or "Export" button
3. Save the CSV file
4. Run: python import_owgr_csv.py rankings.csv
"""

import csv
import sqlite3
from datetime import datetime
import sys

def import_owgr_from_csv(csv_path, db_path='data/cache/pga_data.db'):
    """Import OWGR from CSV file"""

    rankings = {}

    print(f"Reading {csv_path}...")

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Try different CSV formats
            sample = f.read(2048)
            f.seek(0)

            # Detect delimiter
            if '\t' in sample:
                delimiter = '\t'
            else:
                delimiter = ','

            reader = csv.reader(f, delimiter=delimiter)

            # Skip header
            header = next(reader)
            print(f"Header: {header}")
            print()

            # Try to find rank and name columns
            rank_col = None
            name_col = None
            first_name_col = None
            last_name_col = None

            for i, col in enumerate(header):
                col_lower = col.lower().strip()
                if 'ranking' in col_lower and not 'rank' in col_lower:
                    rank_col = i
                elif 'first name' in col_lower or 'firstname' in col_lower:
                    first_name_col = i
                elif 'last name' in col_lower or 'lastname' in col_lower:
                    last_name_col = i
                elif 'name' in col_lower and 'first' not in col_lower and 'last' not in col_lower:
                    name_col = i

            print(f"Found columns: rank={rank_col}, name={name_col}, first={first_name_col}, last={last_name_col}")

            if rank_col is None:
                print("Could not identify rank column, assuming column 1")
                rank_col = 1

            # Read data
            for row in reader:
                try:
                    rank = int(row[rank_col])

                    # Build name from first + last if available, otherwise use name column
                    if first_name_col is not None and last_name_col is not None:
                        first_name = row[first_name_col].strip()
                        last_name = row[last_name_col].strip()
                        name = f"{first_name} {last_name}"
                    elif name_col is not None:
                        name = row[name_col].strip()
                    else:
                        continue

                    if name and rank > 0:
                        rankings[name] = rank

                except (ValueError, IndexError):
                    continue

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if not rankings:
        print("No rankings found in CSV")
        return

    print(f"Loaded {len(rankings)} players")
    print()

    # Show sample
    print("Sample:")
    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
    for player, rank in sorted_rankings[:10]:
        print(f"  #{rank}: {player}")

    # Save to database
    print()
    print("Saving to database...")

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

    print(f"[OK] Saved {len(rankings)} rankings to database")
    print(f"Last updated: {timestamp}")

    # Check for specific players
    print()
    print("Checking specific players:")
    for player in ["Matthieu Pavon", "Scottie Scheffler", "Rory McIlroy"]:
        if player in rankings:
            print(f"  [OK] {player}: #{rankings[player]}")
        else:
            print(f"  [X] {player}: Not found")


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR RANKINGS - CSV IMPORT")
    print("=" * 80)
    print()

    if len(sys.argv) < 2:
        print("Usage: python import_owgr_csv.py <csv_file>")
        print()
        print("To get OWGR CSV file:")
        print("1. Go to https://www.owgr.com/ranking")
        print("2. Set page size to 'All' or a large number (200)")
        print("3. Copy the table data and paste into Excel/Sheets")
        print("4. Export as CSV")
        print("5. Run: python import_owgr_csv.py rankings.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    import_owgr_from_csv(csv_file)

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
