"""
Update 2026 tournament purses from ESPN schedule data
"""

import sqlite3


def update_purses():
    """Update purse data for 2026 tournaments"""

    # Purse data from ESPN schedule page
    purse_data = {
        'Farmers Insurance Open': 9600000,
        'WM Phoenix Open': 9600000,
        'AT&T Pebble Beach Pro-Am': 20000000,
        'The Genesis Invitational': 20000000,
        'Cognizant Classic': 9600000,
        'Arnold Palmer Invitational pres. by Mastercard': 20000000,
        'Arnold Palmer Invitational': 20000000,
        'Puerto Rico Open': 4000000,
        'THE PLAYERS Championship': 25000000,
        'Valspar Championship': 9100000,
        'Texas Children\'s Houston Open': 9900000,
        'Valero Texas Open': 9800000,
        'RBC Heritage': 20000000,
        'Zurich Classic of New Orleans': 9500000,
        'Truist Championship': 20000000,
        'ONEflight Myrtle Beach Classic': 4000000,
        'THE CJ CUP Byron Nelson': 10300000,
        'Charles Schwab Challenge': 9900000,
        'the Memorial Tournament pres. by Workday': 20000000,
        'RBC Canadian Open': 9800000,
        'Travelers Championship': 20000000,
        'John Deere Classic': 8800000,
        'Genesis Scottish Open': 9000000,
        'ISCO Championship': 4000000,
        'Corales Puntacana Championship': 4000000,
        '3M Open': 8800000,
        'Rocket Classic': 10000000,
        'Wyndham Championship': 8500000,
        'FedEx St. Jude Championship': 20000000,
        'BMW Championship': 20000000,
        'TOUR Championship': 40000000,
        'Bank of Utah Championship': 6000000,
        'Baycurrent Classic': 8000000,
        'Butterfield Bermuda Championship': 6000000,
        'VidantaWorld Mexico Open': 6000000,
        'World Wide Technology Championship': 6000000,
        'The RSM Classic': 7400000,
        # Majors - typical purses (may be updated)
        'Masters Tournament': 20000000,
        'PGA Championship': 18000000,
        'U.S. Open': 21500000,
        'The Open': 17000000,
    }

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Make sure purse column exists
    try:
        cursor.execute("ALTER TABLE tournament_2026_ids ADD COLUMN purse INTEGER DEFAULT 0")
        conn.commit()
        print("Added purse column to database")
    except:
        pass

    # Get all tournaments
    cursor.execute("SELECT tournament_name, tournament_id FROM tournament_2026_ids")
    tournaments = cursor.fetchall()

    print(f"Updating purse data for {len(tournaments)} tournaments...")
    print()

    updated = 0
    not_found = []

    for name, tournament_id in tournaments:
        # Try exact match first
        if name in purse_data:
            purse = purse_data[name]
            cursor.execute("""
                UPDATE tournament_2026_ids
                SET purse = ?
                WHERE tournament_id = ?
            """, (purse, tournament_id))
            print(f"[OK] {name}: ${purse:,.0f}")
            updated += 1
        else:
            # Try partial match
            found = False
            for key, purse in purse_data.items():
                if key.lower() in name.lower() or name.lower() in key.lower():
                    cursor.execute("""
                        UPDATE tournament_2026_ids
                        SET purse = ?
                        WHERE tournament_id = ?
                    """, (purse, tournament_id))
                    print(f"[OK] {name}: ${purse:,.0f} (matched to: {key})")
                    updated += 1
                    found = True
                    break

            if not found:
                print(f"[X] {name}: No purse data")
                not_found.append(name)

    conn.commit()
    conn.close()

    print()
    print("=" * 80)
    print(f"COMPLETE: {updated} tournaments updated")
    if not_found:
        print(f"Not found: {len(not_found)} tournaments")
        for name in not_found:
            print(f"  - {name}")
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("UPDATING 2026 TOURNAMENT PURSES")
    print("=" * 80)
    print()

    update_purses()
