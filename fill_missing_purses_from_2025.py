"""
Fill missing 2026 purse data using 2025/2024 tournament earnings
"""

import sqlite3


def fill_missing_purses():
    """Fill missing purse data from 2025 earnings"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Add purse_override column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE tournament_2026_ids ADD COLUMN purse_override INTEGER")
        conn.commit()
    except:
        pass  # Column already exists

    # Get tournaments with missing purse data (skip those with a manual override)
    cursor.execute("""
        SELECT tournament_name, tournament_id
        FROM tournament_2026_ids
        WHERE (purse = 0 OR purse IS NULL)
        AND purse_override IS NULL
        ORDER BY date
    """)
    missing_purse_tournaments = cursor.fetchall()

    print(f"Found {len(missing_purse_tournaments)} tournaments with missing purse data")
    print()

    updated = 0

    for tournament_name, tournament_id in missing_purse_tournaments:
        # Try to find matching tournament in 2025 data first, then 2024 as fallback
        # Try exact match first
        total_purse = None
        year_used = None

        for year in [2025, 2024]:
            cursor.execute("""
                SELECT SUM(earnings) as total_purse
                FROM tournament_results
                WHERE tournament_name = ?
                AND year = ?
                AND earnings > 0
            """, (tournament_name, year))

            result = cursor.fetchone()
            if result and result[0] and result[0] > 0:
                total_purse = result[0]
                year_used = year
                break

        # If no exact match, try partial match
        if not total_purse:
            # Extract key words from tournament name
            keywords = tournament_name.lower().replace('pres. by', '').replace('presented by', '')

            # Try to find similar tournament in 2025 or 2024
            for year in [2025, 2024]:
                if total_purse:
                    break

                cursor.execute("""
                    SELECT tournament_name, SUM(earnings) as total_purse
                    FROM tournament_results
                    WHERE year = ?
                    AND earnings > 0
                    GROUP BY tournament_name
                """, (year,))

                all_tournaments = cursor.fetchall()

                # Look for partial matches
                for t_name, t_purse in all_tournaments:
                    if not t_name:
                        continue
                    # Simple matching - check if key words overlap
                    if tournament_name.split()[0].lower() in t_name.lower():
                        # Check if it's a reasonable match
                        name_parts = tournament_name.lower().split()
                        t_name_lower = t_name.lower()

                        matches = sum(1 for part in name_parts if len(part) > 3 and part in t_name_lower)

                        if matches >= 2:  # At least 2 significant words match
                            total_purse = t_purse
                            year_used = year
                            print(f"[MATCH] {tournament_name} -> {t_name} ({year}): ${total_purse:,.0f}")
                            break

        if total_purse and total_purse > 0:
            # Round to nearest 100k for cleaner numbers
            total_purse = round(total_purse / 100000) * 100000

            cursor.execute("""
                UPDATE tournament_2026_ids
                SET purse = ?
                WHERE tournament_id = ?
            """, (int(total_purse), tournament_id))

            print(f"[OK] {tournament_name}: ${total_purse:,.0f} (from {year_used} data)")
            updated += 1
        else:
            print(f"[X] {tournament_name}: No earnings data found")

    conn.commit()
    conn.close()

    print()
    print("=" * 80)
    print(f"COMPLETE: {updated} tournaments updated from historical data")
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("FILLING MISSING 2026 PURSES FROM HISTORICAL DATA (2025/2024)")
    print("=" * 80)
    print()

    fill_missing_purses()
