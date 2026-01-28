"""
Create player name aliases table for known variations
"""

import sqlite3

def create_aliases_table():
    """Create table for player name aliases"""

    conn = sqlite3.connect('data/cache/pga_data.db')
    cursor = conn.cursor()

    # Create aliases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_aliases (
            alias_name TEXT PRIMARY KEY,
            official_name TEXT NOT NULL,
            notes TEXT
        )
    """)

    # Common aliases - Western names, initials, name variations, disambiguation
    aliases = [
        ('Kevin Yu', 'Chun-an Yu', 'Uses Western first name'),
        ('C.T. Pan', 'Cheng-Tsung Pan', 'Uses initials'),
        ('K.H. Lee', 'Kyoung-Hoon Lee', 'Uses initials'),
        ('S.H. Kim', 'Si Woo Kim', 'Uses initials (sometimes)'),
        ('Byeong Hun An', 'Ben An', 'Uses both names'),
        ('Ben An', 'Byeong Hun An', 'Reverse alias'),
        ('Zecheng Dou', 'Marty Dou Zecheng', 'Uses part of full name'),
        ('Daniel Brown', 'Daniel Brown(Oct1994)', 'Birth date disambiguation'),
        ('Dan Brown', 'Daniel Brown(Oct1994)', 'Shortened first name'),
    ]

    for alias, official, notes in aliases:
        cursor.execute("""
            INSERT OR REPLACE INTO player_aliases (alias_name, official_name, notes)
            VALUES (?, ?, ?)
        """, (alias, official, notes))

    conn.commit()
    conn.close()

    print(f"Created aliases table with {len(aliases)} entries")
    print()
    print("Aliases:")
    for alias, official, notes in aliases:
        print(f"  '{alias}' -> '{official}' ({notes})")

if __name__ == "__main__":
    print("=" * 80)
    print("CREATING PLAYER NAME ALIASES")
    print("=" * 80)
    print()

    create_aliases_table()

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
