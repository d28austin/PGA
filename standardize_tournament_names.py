"""
Standardize tournament names that refer to the same tournament
"""

import sqlite3

# Mapping of variant names to standardized names
# Key: current name in database, Value: standardized name to use
TOURNAMENT_NAME_MAPPING = {
    # Masters Tournament
    '2020 Masters Tournament': 'Masters Tournament',
    '2021 Masters Tournament': 'Masters Tournament',

    # Arnold Palmer Invitational
    'Arnold Palmer Invitational Pres. By Mastercard': 'Arnold Palmer Invitational',
    'Arnold Palmer Invitational pres. by Mastercard': 'Arnold Palmer Invitational',

    # Phoenix Open
    'Waste Management Phoenix Open': 'WM Phoenix Open',

    # Mexico Open
    'Mexico Open': 'Mexico Open at Vidanta',
    'Mexico Open at VidantaWorld': 'Mexico Open at Vidanta',

    # Memorial Tournament
    'the Memorial Tournament pres. by Nationwide': 'The Memorial Tournament',
    'The Memorial Tournament pres. by Workday': 'The Memorial Tournament',
    'the Memorial Tournament pres. by Workday': 'The Memorial Tournament',

    # Tour Championship
    'Tour Championship': 'TOUR Championship',

    # The Open Championship
    'The Open Championship': 'The Open',

    # Sentry
    'Sentry Tournament of Champions': 'The Sentry',

    # Houston Open
    'Houston Open': 'Cadence Bank Houston Open',
    'Vivint Houston Open': 'Cadence Bank Houston Open',
    "Texas Children's Houston Open": 'Cadence Bank Houston Open',

    # Cognizant Classic
    'Cognizant Classic': 'Cognizant Classic in The Palm Beaches',

    # Corales Puntacana
    'Corales Puntacana Resort & Club Championship': 'Corales Puntacana Championship',

    # Mayakoba
    'Mayakoba Golf Classic': 'World Wide Technology Championship at Mayakoba',
    'Mayakoba Golf Classic presented by UNIFIN': 'World Wide Technology Championship at Mayakoba',
    'World Wide Technology Championship': 'World Wide Technology Championship at Mayakoba',

    # Shriners
    'Shriners Hospitals for Children Open': "Shriners Children's Open",

    # CJ CUP
    'THE CJ CUP @ NINE BRIDGES': 'THE CJ CUP',
    'THE CJ CUP @ SHADOW CREEK': 'THE CJ CUP',
    'THE CJ CUP @ SUMMIT': 'THE CJ CUP',
    'THE CJ CUP in South Carolina': 'THE CJ CUP',
    # Note: "THE CJ CUP Byron Nelson" is different - it's the Byron Nelson tournament

    # FedEx St. Jude
    'WGC-FedEx St. Jude Invitational': 'FedEx St. Jude Championship',

    # Myrtle Beach
    'Myrtle Beach Classic': 'ONEflight Myrtle Beach Classic',

    # Rocket Mortgage
    'Rocket Classic': 'Rocket Mortgage Classic',

    # Safeway/Fortinet (same tournament, renamed)
    'Safeway Open': 'Fortinet Championship',

    # Northern Trust / FedEx Playoffs
    'THE NORTHERN TRUST': 'FedEx St. Jude Championship',

    # ZOZO Championship
    'The ZOZO CHAMPIONSHIP': 'ZOZO CHAMPIONSHIP',
}


def standardize_names():
    """Apply standardized tournament names to database"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("STANDARDIZING TOURNAMENT NAMES")
    print("=" * 80)
    print()

    total_updated = 0

    for old_name, new_name in TOURNAMENT_NAME_MAPPING.items():
        # Check if old name exists
        cursor.execute('''
            SELECT COUNT(*) FROM tournament_results
            WHERE tournament_name = ?
        ''', (old_name,))

        count = cursor.fetchone()[0]

        if count > 0:
            print(f"Updating '{old_name}'")
            print(f"     -> '{new_name}' ({count} records)")

            cursor.execute('''
                UPDATE tournament_results
                SET tournament_name = ?
                WHERE tournament_name = ?
            ''', (new_name, old_name))

            total_updated += count
        else:
            print(f"Skipping '{old_name}' (not found in database)")

    conn.commit()

    print()
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print()

    # Count unique tournament names after standardization
    cursor.execute('''
        SELECT COUNT(DISTINCT tournament_name)
        FROM tournament_results
        WHERE tournament_name IS NOT NULL AND tournament_id != 'T001'
    ''')

    unique_count = cursor.fetchone()[0]

    print(f"Total records updated: {total_updated}")
    print(f"Unique tournament names after standardization: {unique_count}")
    print()

    # Show tournaments with multiple years
    cursor.execute('''
        SELECT tournament_name, COUNT(DISTINCT year) as years,
               MIN(year) as first, MAX(year) as last,
               COUNT(*) as records
        FROM tournament_results
        WHERE tournament_name IS NOT NULL AND tournament_id != 'T001'
        GROUP BY tournament_name
        HAVING years > 1
        ORDER BY years DESC, tournament_name
        LIMIT 20
    ''')

    print("Top tournaments by year count:")
    for name, years, first, last, records in cursor.fetchall():
        year_range = f"{first}-{last}" if years > 1 else str(first)
        print(f"  {name:50} | {years} years ({year_range}) | {records} records")

    conn.close()

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Successfully standardized {len([k for k, v in TOURNAMENT_NAME_MAPPING.items() if v])} tournament name variants")


if __name__ == "__main__":
    try:
        standardize_names()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
