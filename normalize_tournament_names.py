"""
Normalize Tournament Names
Standardizes tournament names across all years to ensure consistent aggregation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import sqlite3
from data.database import PGADatabase


# Tournament name normalization mapping
# Maps variations to the canonical name
TOURNAMENT_NAME_MAPPINGS = {
    # Phoenix Open
    'Waste Management Phoenix Open': 'WM Phoenix Open',

    # Pebble Beach
    'AT&T Pebble Beach National Pro-Am': 'AT&T Pebble Beach Pro-Am',

    # Genesis Invitational (not Genesis Open which was different)
    'Genesis Open': 'The Genesis Invitational',

    # Arnold Palmer Invitational - all variations
    'Arnold Palmer Invitational Pres. By Mastercard': 'Arnold Palmer Invitational',
    'Arnold Palmer Invitational pres. by Mastercard': 'Arnold Palmer Invitational',
    'Arnold Palmer Invitational presented by MasterCard': 'Arnold Palmer Invitational',
    'Arnold Palmer Invitational presented by Mastercard': 'Arnold Palmer Invitational',

    # THE PLAYERS Championship
    'The Players Championship': 'THE PLAYERS Championship',

    # Memorial Tournament - all variations
    'the Memorial Tournament pres. by Nationwide': 'the Memorial Tournament',
    'the Memorial Tournament pres. by Workday': 'the Memorial Tournament',
    'the Memorial Tournament presented by Nationwide': 'the Memorial Tournament',
    'the Memorial Tournament presented by Nationwide Insurance': 'the Memorial Tournament',

    # Zurich Classic
    'Zurich Classic of New Orleans': 'Zurich Classic of New Orleans',

    # Wells Fargo
    'Wells Fargo Championship': 'Wells Fargo Championship',

    # Byron Nelson
    'HP Byron Nelson Championship': 'THE CJ CUP Byron Nelson',
    'AT&T Byron Nelson': 'THE CJ CUP Byron Nelson',
    'CJ CUP Byron Nelson': 'THE CJ CUP Byron Nelson',
    'THE CJ CUP Byron Nelson': 'THE CJ CUP Byron Nelson',

    # Charles Schwab Challenge
    'Charles Schwab Challenge': 'Charles Schwab Challenge',
    'Dean & DeLuca Invitational': 'Charles Schwab Challenge',
    'Fort Worth Invitational': 'Charles Schwab Challenge',

    # RBC Heritage
    'RBC Heritage': 'RBC Heritage',

    # Valspar Championship
    'Valspar Championship': 'Valspar Championship',

    # Houston Open
    'Houston Open': "Texas Children's Houston Open",
    'Shell Houston Open': "Texas Children's Houston Open",
    'Texas Children Houston Open': "Texas Children's Houston Open",
    'Cadence Bank Houston Open': "Texas Children's Houston Open",
    "Texas Children's Houston Open": "Texas Children's Houston Open",

    # Valero Texas Open
    'Valero Texas Open': 'Valero Texas Open',

    # Wyndham Championship
    'Wyndham Championship': 'Wyndham Championship',

    # FedEx Cup Playoffs
    'FedEx St. Jude Championship': 'FedEx St. Jude Championship',
    'FedEx St. Jude Invitational': 'FedEx St. Jude Championship',
    'WGC-FedEx St. Jude Invitational': 'FedEx St. Jude Championship',
    'St. Jude Classic': 'FedEx St. Jude Championship',
    'FedEx St. Jude Classic': 'FedEx St. Jude Championship',

    'BMW Championship': 'BMW Championship',

    'TOUR Championship': 'TOUR Championship',
    'The Tour Championship': 'TOUR Championship',
    'TOUR Championship by Coca-Cola': 'TOUR Championship',
    'Tour Championship': 'TOUR Championship',

    # The Barclays / Northern Trust / Liberty National
    'The Barclays': 'The Northern Trust',
    'The Northern Trust': 'The Northern Trust',

    # Deutsche Bank / Dell Technologies
    'Deutsche Bank Championship': 'BMW Championship',
    'Dell Technologies Championship': 'BMW Championship',

    # 3M Open
    '3M Open': '3M Open',

    # Rocket Classic
    'Rocket Mortgage Classic': 'Rocket Classic',
    'Rocket Classic': 'Rocket Classic',

    # Travelers Championship
    'Travelers Championship': 'Travelers Championship',

    # U.S. Open
    'U.S. Open': 'U.S. Open',
    'US Open': 'U.S. Open',
    'U.S. Open Golf Championship': 'U.S. Open',

    # The Open Championship
    'The Open Championship': 'The Open',
    'The Open': 'The Open',
    'British Open': 'The Open',

    # PGA Championship
    'PGA Championship': 'PGA Championship',

    # Masters
    'Masters Tournament': 'Masters Tournament',
    'The Masters': 'Masters Tournament',
    '2017 Masters Tournament': 'Masters Tournament',
    '2018 Masters Tournament': 'Masters Tournament',
    '2019 Masters Tournament': 'Masters Tournament',

    # Sanderson Farms / Country Club of Jackson
    'Sanderson Farms Championship': 'Sanderson Farms Championship',
    'Country Club of Jackson Championship': 'Sanderson Farms Championship',

    # Shriners / Las Vegas
    'Shriners Hospitals for Children Open': 'Shriners Children\'s Open',
    'Shriners Children\'s Open': 'Shriners Children\'s Open',

    # CJ Cup
    'CJ Cup @ Nine Bridges': 'CJ Cup',
    'CJ Cup @ Shadow Creek': 'CJ Cup',
    'CJ Cup in South Carolina': 'CJ Cup',
    'The CJ Cup': 'CJ Cup',

    # Zozo Championship
    'ZOZO Championship': 'ZOZO Championship',
    'Zozo Championship': 'ZOZO Championship',

    # RSM Classic
    'The RSM Classic': 'The RSM Classic',
    'RSM Classic': 'The RSM Classic',

    # Hero World Challenge
    'Hero World Challenge': 'Hero World Challenge',

    # Sony Open
    'Sony Open in Hawaii': 'Sony Open in Hawaii',

    # The American Express
    'CareerBuilder Challenge': 'The American Express',
    'Humana Challenge': 'The American Express',
    'The American Express': 'The American Express',

    # Farmers Insurance Open
    'Farmers Insurance Open': 'Farmers Insurance Open',

    # WGC Events
    'WGC-Dell Technologies Match Play': 'WGC-Dell Technologies Match Play',
    'WGC-Dell Match Play': 'WGC-Dell Technologies Match Play',
    'WGC-Cadillac Match Play': 'WGC-Dell Technologies Match Play',

    'WGC-Mexico Championship': 'WGC-Mexico Championship',
    'WGC-Cadillac Championship': 'WGC-Mexico Championship',

    'WGC-Workday Championship': 'WGC-Workday Championship',

    'WGC-HSBC Champions': 'WGC-HSBC Champions',

    'WGC-Bridgestone Invitational': 'WGC-Bridgestone Invitational',

    # Puerto Rico Open
    'Puerto Rico Open': 'Puerto Rico Open',

    # Corales Puntacana Championship
    'Corales Puntacana Resort & Club Championship': 'Corales Puntacana Championship',
    'Corales Puntacana Championship': 'Corales Puntacana Championship',

    # Mayakoba / World Wide Technology Championship
    'Mayakoba Golf Classic': 'World Wide Technology Championship',
    'World Wide Technology Championship at Mayakoba': 'World Wide Technology Championship',
    'World Wide Technology Championship': 'World Wide Technology Championship',

    # Butterfield Bermuda Championship
    'Butterfield Bermuda Championship': 'Butterfield Bermuda Championship',

    # Mexico Open
    'Mexico Open': 'Mexico Open',
    'Mexico Open at Vidanta': 'Mexico Open',

    # Myrtle Beach Classic
    'Myrtle Beach Classic': 'Myrtle Beach Classic',

    # Black Desert Championship
    'Black Desert Championship': 'Black Desert Championship',

    # Cognizant Classic
    'Cognizant Classic': 'The Honda Classic',
    'Honda Classic': 'The Honda Classic',
    'The Honda Classic': 'The Honda Classic',

    # Sentry
    'Sentry Tournament of Champions': 'The Sentry',
    'Hyundai Tournament of Champions': 'The Sentry',
    'The Sentry': 'The Sentry',
}


def normalize_tournament_names():
    """Update tournament names in the database to use canonical names"""

    db = PGADatabase()
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    print("Normalizing tournament names...")
    print("=" * 80)

    total_updates = 0

    for old_name, new_name in TOURNAMENT_NAME_MAPPINGS.items():
        if old_name == new_name:
            continue

        # Update tournament_results
        cursor.execute("""
            SELECT COUNT(*) FROM tournament_results WHERE tournament_name = ?
        """, (old_name,))
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute("""
                UPDATE tournament_results
                SET tournament_name = ?
                WHERE tournament_name = ?
            """, (new_name, old_name))

            total_updates += count
            print(f"Updated {count:4d} records: '{old_name}' -> '{new_name}'")

    # Also normalize tournament_2026_ids so 2026 names match historical canonical names
    print()
    print("Normalizing 2026 schedule names...")
    schedule_updates = 0

    for old_name, new_name in TOURNAMENT_NAME_MAPPINGS.items():
        if old_name == new_name:
            continue

        cursor.execute("""
            SELECT COUNT(*) FROM tournament_2026_ids WHERE tournament_name = ?
        """, (old_name,))
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute("""
                UPDATE tournament_2026_ids
                SET tournament_name = ?
                WHERE tournament_name = ?
            """, (new_name, old_name))

            schedule_updates += count
            print(f"Updated 2026 schedule: '{old_name}' -> '{new_name}'")

    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"Total tournament_results updated: {total_updates}")
    print(f"Total tournament_2026_ids updated: {schedule_updates}")
    print("Tournament name normalization complete!")


if __name__ == "__main__":
    normalize_tournament_names()
