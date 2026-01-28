"""
Remove tournaments that share the same date, keeping the one with highest purse
"""

import sqlite3
import pandas as pd


def remove_duplicate_dates():
    """Remove lower-purse tournaments that share dates"""

    conn = sqlite3.connect('data/cache/pga_data.db')

    # Get all tournaments with dates
    df = pd.read_sql("""
        SELECT tournament_name, tournament_id, date, purse
        FROM tournament_2026_ids
        ORDER BY date, purse DESC
    """, conn)

    print(f"Total tournaments: {len(df)}")
    print()

    # Parse dates
    df['date_parsed'] = pd.to_datetime(df['date'], utc=True)
    df['date_only'] = df['date_parsed'].dt.date

    # Find dates with multiple tournaments
    date_counts = df['date_only'].value_counts()
    duplicate_dates = date_counts[date_counts > 1]

    if len(duplicate_dates) == 0:
        print("No duplicate dates found!")
        conn.close()
        return

    print(f"Found {len(duplicate_dates)} dates with multiple tournaments:")
    print()

    to_remove = []

    for date, count in duplicate_dates.items():
        tournaments_on_date = df[df['date_only'] == date].copy()
        tournaments_on_date = tournaments_on_date.sort_values('purse', ascending=False)

        print(f"Date: {date} ({count} tournaments)")

        # Keep the first one (highest purse), mark rest for removal
        keeper = tournaments_on_date.iloc[0]
        remove_list = tournaments_on_date.iloc[1:]

        print(f"  KEEPING: {keeper['tournament_name']} (${keeper['purse']:,.0f})")

        for _, tournament in remove_list.iterrows():
            print(f"  REMOVING: {tournament['tournament_name']} (${tournament['purse']:,.0f})")
            to_remove.append(tournament['tournament_id'])

        print()

    if len(to_remove) == 0:
        print("No tournaments to remove")
        conn.close()
        return

    # Remove tournaments
    cursor = conn.cursor()

    for tournament_id in to_remove:
        cursor.execute("""
            DELETE FROM tournament_2026_ids
            WHERE tournament_id = ?
        """, (tournament_id,))

    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"COMPLETE: Removed {len(to_remove)} tournaments with duplicate dates")
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("REMOVING DUPLICATE DATE TOURNAMENTS")
    print("=" * 80)
    print()

    remove_duplicate_dates()
