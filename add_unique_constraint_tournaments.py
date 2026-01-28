"""
Add unique constraint to tournaments table to prevent duplicate tournament_ids
"""

import sqlite3


def add_unique_constraint(db_path: str = "data/cache/pga_data.db"):
    """Add unique constraint to tournament_id in tournaments table"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Adding unique constraint to tournaments table...")
    print("="*60)

    try:
        # Check if we need to recreate the table
        # SQLite doesn't support adding constraints to existing tables directly
        # We need to create a new table and copy data

        # Drop tournaments_new if it exists from a failed attempt
        cursor.execute("DROP TABLE IF EXISTS tournaments_new")

        # Create new table with unique constraint
        cursor.execute("""
            CREATE TABLE tournaments_new (
                event_id TEXT,
                name TEXT,
                start_date TEXT,
                end_date TEXT,
                year INTEGER,
                tournament_id TEXT PRIMARY KEY UNIQUE,
                tournament_name TEXT,
                last_updated TIMESTAMP,
                par_per_round INTEGER,
                total_par INTEGER,
                rounds INTEGER,
                num_courses INTEGER
            )
        """)

        # Copy data from old table to new table (will skip duplicates due to PRIMARY KEY)
        cursor.execute("""
            INSERT OR IGNORE INTO tournaments_new
            (event_id, name, start_date, end_date, year, tournament_id, tournament_name,
             last_updated, par_per_round, total_par, rounds, num_courses)
            SELECT event_id, name, start_date, end_date, year, tournament_id, tournament_name,
                   last_updated, par_per_round, total_par, rounds, num_courses
            FROM tournaments
        """)

        # Drop old table
        cursor.execute("DROP TABLE tournaments")

        # Rename new table
        cursor.execute("ALTER TABLE tournaments_new RENAME TO tournaments")

        conn.commit()

        print("[OK] Successfully added unique constraint to tournaments table")
        print("     tournament_id is now the PRIMARY KEY and UNIQUE")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM tournaments")
        count = cursor.fetchone()[0]
        print(f"     Total tournaments: {count}")

    except Exception as e:
        print(f"[ERROR] Failed to add constraint: {e}")
        conn.rollback()
    finally:
        conn.close()

    print("="*60)


if __name__ == "__main__":
    add_unique_constraint()
