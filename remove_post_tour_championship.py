"""
Remove all tournaments that occur after the TOUR Championship
"""

import sqlite3
import pandas as pd


def remove_post_tour_championship():
    """Remove tournaments after TOUR Championship"""

    conn = sqlite3.connect('data/cache/pga_data.db')

    # Get TOUR Championship date
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tournament_name, tournament_id, date
        FROM tournament_2026_ids
        WHERE tournament_name LIKE '%TOUR Championship%'
    """)

    tour_champ = cursor.fetchone()

    if not tour_champ:
        print("TOUR Championship not found!")
        conn.close()
        return

    tour_champ_name, tour_champ_id, tour_champ_date = tour_champ
    print(f"TOUR Championship: {tour_champ_name}")
    print(f"Date: {tour_champ_date}")
    print()

    # Get all tournaments after TOUR Championship
    df = pd.read_sql("""
        SELECT tournament_name, tournament_id, date, purse
        FROM tournament_2026_ids
        ORDER BY date
    """, conn)

    df['date_parsed'] = pd.to_datetime(df['date'], utc=True)
    tour_champ_date_parsed = pd.to_datetime(tour_champ_date, utc=True)

    # Find tournaments after TOUR Championship
    after_tour_champ = df[df['date_parsed'] > tour_champ_date_parsed]

    if len(after_tour_champ) == 0:
        print("No tournaments found after TOUR Championship")
        conn.close()
        return

    print(f"Found {len(after_tour_champ)} tournaments after TOUR Championship:")
    print()

    for _, tournament in after_tour_champ.iterrows():
        purse_str = f"${tournament['purse']:,.0f}" if tournament['purse'] > 0 else "No purse"
        print(f"  - {tournament['tournament_name']} ({tournament['date_parsed'].strftime('%b %d, %Y')}) - {purse_str}")

    # Remove tournaments
    tournament_ids = after_tour_champ['tournament_id'].tolist()

    for tournament_id in tournament_ids:
        cursor.execute("""
            DELETE FROM tournament_2026_ids
            WHERE tournament_id = ?
        """, (tournament_id,))

    conn.commit()
    conn.close()

    print()
    print("=" * 80)
    print(f"COMPLETE: Removed {len(tournament_ids)} tournaments after TOUR Championship")
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("REMOVING POST-TOUR CHAMPIONSHIP TOURNAMENTS")
    print("=" * 80)
    print()

    remove_post_tour_championship()
