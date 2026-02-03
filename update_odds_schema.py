"""
Update odds database schema to support multiple market types
Adds 'market_type' column and labels existing odds as 'Win'
"""

import sqlite3

def update_odds_schema():
    """Add market_type column and update existing data"""

    db_path = "data/cache/pga_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("="*60)
    print("UPDATING ODDS DATABASE SCHEMA")
    print("="*60)

    # Check if market_type column already exists
    cursor.execute("PRAGMA table_info(weekly_odds)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'market_type' not in columns:
        print("\nAdding 'market_type' column...")

        # Add market_type column
        cursor.execute("""
            ALTER TABLE weekly_odds
            ADD COLUMN market_type TEXT DEFAULT 'Win'
        """)

        print("OK Column added")
    else:
        print("\n'market_type' column already exists")

    # Update existing odds to have market_type = 'Win'
    print("\nUpdating existing odds to market_type='Win'...")
    cursor.execute("""
        UPDATE weekly_odds
        SET market_type = 'Win'
        WHERE market_type IS NULL OR market_type = ''
    """)

    updated_count = cursor.rowcount
    print(f"OK Updated {updated_count} odds")

    conn.commit()

    # Show summary
    print("\n" + "="*60)
    print("CURRENT ODDS SUMMARY")
    print("="*60)

    cursor.execute("""
        SELECT bookmaker, market_type, COUNT(*) as cnt
        FROM weekly_odds
        GROUP BY bookmaker, market_type
        ORDER BY bookmaker, market_type
    """)

    print("\nOdds by bookmaker and market:")
    for bookmaker, market, count in cursor.fetchall():
        print(f"  {bookmaker:15s} {market:10s} {count:3d} odds")

    cursor.execute("SELECT COUNT(*) FROM weekly_odds")
    total = cursor.fetchone()[0]
    print(f"\nTotal: {total} odds")

    conn.close()

    print("\n" + "="*60)
    print("SCHEMA UPDATE COMPLETE")
    print("="*60)
    print("\nReady to scrape Top 10 odds!")

if __name__ == "__main__":
    update_odds_schema()
