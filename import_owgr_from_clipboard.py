"""
Import OWGR rankings from clipboard
Simple workflow: Copy table from OWGR.com website, run this script
"""

import sqlite3
from datetime import datetime
import pyperclip
import re

def import_owgr_from_clipboard(db_path='data/cache/pga_data.db'):
    """
    Import OWGR rankings from clipboard

    Instructions:
    1. Go to https://www.owgr.com/ranking
    2. Set page size to 200 or All
    3. Select all table data (Ctrl+A then copy just the table)
    4. Run this script
    """

    try:
        # Read from clipboard
        clipboard_data = pyperclip.paste()

        if not clipboard_data:
            print("Clipboard is empty!")
            print()
            print("Instructions:")
            print("1. Go to https://www.owgr.com/ranking")
            print("2. Select table data and copy (Ctrl+C)")
            print("3. Run this script again")
            return

        print("Found clipboard data")
        print(f"Length: {len(clipboard_data)} characters")
        print()

        # Parse the data
        # Expected format: rank name country points (tab or space separated)
        lines = clipboard_data.strip().split('\n')

        rankings = {}
        parsed = 0

        for line in lines:
            # Clean up the line
            line = line.strip()

            if not line:
                continue

            # Try to extract rank and name
            # Format is usually: "1 Scottie Scheffler USA ..." or "1\tScottie Scheffler\tUSA..."
            parts = re.split(r'[\t\s]+', line)

            if len(parts) >= 2:
                try:
                    # First part should be rank
                    rank = int(parts[0])

                    # Name could be 2-3 parts (first name + last name, sometimes middle)
                    # Look for the country code (2-3 letters uppercase) to know where name ends
                    name_parts = []
                    for i in range(1, len(parts)):
                        part = parts[i]
                        # If it's a 2-3 letter uppercase code, we've hit the country
                        if len(part) <= 3 and part.isupper() and part.isalpha():
                            break
                        # If it looks like a number or decimal, skip
                        try:
                            float(part.replace(',', ''))
                            break
                        except:
                            name_parts.append(part)

                    if name_parts:
                        name = ' '.join(name_parts)
                        if len(name) > 3:  # Reasonable name length
                            rankings[name] = rank
                            parsed += 1

                except (ValueError, IndexError):
                    continue

        print(f"Parsed {parsed} players from clipboard")

        if not rankings:
            print()
            print("Could not parse any rankings!")
            print("Sample of clipboard content:")
            print(clipboard_data[:500])
            return

        # Show sample
        print()
        print("Sample of parsed data:")
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
        for player, rank in sorted_rankings[:10]:
            print(f"  #{rank}: {player}")

        # Save to database
        print()
        print("Saving to database...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table
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

        # Check for Matthieu Pavon
        if "Matthieu Pavon" in rankings:
            print()
            print(f"[OK] Matthieu Pavon: Ranked #{rankings['Matthieu Pavon']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        import pyperclip
    except ImportError:
        print("pyperclip not installed!")
        print("Install with: pip install pyperclip")
        exit(1)

    print("=" * 80)
    print("OWGR RANKINGS - CLIPBOARD IMPORT")
    print("=" * 80)
    print()

    import_owgr_from_clipboard()

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
