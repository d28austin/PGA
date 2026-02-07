"""
Database module for storing and retrieving PGA data
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta


class PGADatabase:
    """SQLite database for caching PGA data"""

    def __init__(self, db_path: str = "data/cache/pga_data.db"):
        self.db_path = db_path
        self._current_user: Optional[str] = None
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @current_user.setter
    def current_user(self, value: Optional[str]):
        self._current_user = value

    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tournaments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
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


        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                last_updated TIMESTAMP
            )
        """)

        # Tournament results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournament_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                tournament_name TEXT,
                tournament_id TEXT,
                year INTEGER,
                position TEXT,
                total_score INTEGER,
                earnings REAL,
                rounds_played INTEGER,
                last_updated TIMESTAMP,
                UNIQUE(player_id, tournament_id, year)
            )
        """)

        # 2026 schedule table (populated from ESPN scoreboard API)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournament_2026_ids (
                tournament_name TEXT PRIMARY KEY,
                tournament_id TEXT NOT NULL,
                date TEXT,
                status TEXT,
                purse INTEGER DEFAULT 0,
                purse_override INTEGER
            )
        """)

        # Add purse_override column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE tournament_2026_ids ADD COLUMN purse_override INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Used players table (for one-and-done tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS used_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                tournament_name TEXT NOT NULL,
                week_used TEXT,
                date_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_name, tournament_name)
            )
        """)

        # OWGR rankings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS owgr_rankings (
                player_name TEXT PRIMARY KEY,
                ranking INTEGER,
                last_updated TIMESTAMP
            )
        """)

        # Player aliases table (for OWGR name matching)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_aliases (
                alias_name TEXT PRIMARY KEY,
                official_name TEXT NOT NULL,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

    def save_tournaments(self, tournaments_df: pd.DataFrame):
        """Save tournament schedule to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        last_updated = datetime.now()

        # Use INSERT OR REPLACE to handle existing tournaments with unique constraint
        for _, row in tournaments_df.iterrows():
            # Convert values to appropriate types for SQLite
            def get_value(col_name):
                val = row.get(col_name, None)
                if pd.isna(val):
                    return None
                return val

            cursor.execute("""
                INSERT OR REPLACE INTO tournaments
                (event_id, name, start_date, end_date, year, tournament_id, tournament_name,
                 last_updated, par_per_round, total_par, rounds, num_courses)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                get_value('event_id'),
                get_value('name'),
                get_value('start_date'),
                get_value('end_date'),
                get_value('year'),
                get_value('tournament_id'),
                get_value('tournament_name'),
                last_updated,  # Use datetime.now() directly instead of from dataframe
                get_value('par_per_round'),
                get_value('total_par'),
                get_value('rounds'),
                get_value('num_courses')
            ))

        conn.commit()
        conn.close()

    def save_tournament_results(self, results_df: pd.DataFrame):
        """Save tournament results to database"""
        if results_df.empty:
            return

        conn = sqlite3.connect(self.db_path)
        results_df['last_updated'] = datetime.now()

        # Use replace to update existing records
        for _, row in results_df.iterrows():
            # Helper function to clean values
            def clean_value(value, as_str=True):
                """Convert value to simple type suitable for SQLite"""
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    return None
                if isinstance(value, dict) or isinstance(value, list):
                    return str(value) if as_str else None
                if as_str:
                    return str(value)
                return value

            def clean_numeric(value):
                """Convert value to numeric or None"""
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    return None
                if isinstance(value, (dict, list)):
                    return None
                try:
                    return float(value) if value != '' else None
                except (ValueError, TypeError):
                    return None

            # Clean all values
            player_id = clean_value(row.get('player_id'))
            player_name = clean_value(row.get('player_name'))
            tournament_name = clean_value(row.get('tournament_name'))
            tournament_id = clean_value(row.get('tournament_id'))
            year = clean_numeric(row.get('year'))
            position = clean_value(row.get('position'))
            total_score = clean_numeric(row.get('total_score'))
            earnings = clean_numeric(row.get('earnings'))
            rounds_played = clean_numeric(row.get('rounds_played'))

            conn.execute("""
                INSERT OR REPLACE INTO tournament_results
                (player_id, player_name, tournament_name, tournament_id, year, position, total_score, earnings, rounds_played, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                player_name,
                tournament_name,
                tournament_id,
                year,
                position,
                total_score,
                earnings,
                rounds_played,
                datetime.now()
            ))

        conn.commit()
        conn.close()

    def save_owgr_rankings(self, rankingings_df: pd.DataFrame):
        """Save OWGR rankingings to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create OWGR table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS owgr_rankings (
                player_name TEXT PRIMARY KEY,
                ranking INTEGER,
                last_updated TIMESTAMP
            )
        """)

        # Clear old rankingings and insert new ones
        cursor.execute("DELETE FROM owgr_rankings")

        for _, row in rankingings_df.iterrows():
            cursor.execute("""
                INSERT INTO owgr_rankings (player_name, ranking, last_updated)
                VALUES (?, ?, ?)
            """, (row['player_name'], row['ranking'], datetime.now()))

        conn.commit()
        conn.close()

    def get_player_owgr(self, player_name: str) -> int:
        """Get a player's OWGR ranking"""

        # Common name abbreviations mapping
        name_variations = {
            'Sam': 'Samuel', 'Cam': 'Cameron', 'Matt': 'Matthew', 'Mike': 'Michael',
            'Rob': 'Robert', 'Bob': 'Robert', 'Bill': 'William', 'Will': 'William',
            'Tom': 'Thomas', 'Tony': 'Anthony', 'Dan': 'Daniel', 'Dave': 'David',
            'Chris': 'Christopher', 'Jim': 'James', 'Jimmy': 'James', 'Joe': 'Joseph',
            'Pat': 'Patrick', 'Rick': 'Richard', 'Steve': 'Steven', 'Tim': 'Timothy',
            'Ben': 'Benjamin', 'Alex': 'Alexander', 'Nick': 'Nicholas', 'Max': 'Maximilian',
            'Seb': 'Sebastian', 'Xander': 'Alexander'
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Bail out early if owgr_rankings table doesn't exist yet
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='owgr_rankings'")
        if not cursor.fetchone():
            conn.close()
            return None

        # Check aliases first (e.g., Kevin Yu -> Chun-an Yu)
        try:
            cursor.execute("""
                SELECT official_name FROM player_aliases
                WHERE alias_name = ?
            """, (player_name,))
            alias_result = cursor.fetchone()
            if alias_result:
                player_name = alias_result[0]
        except sqlite3.OperationalError:
            pass  # Table may not exist yet

        # Try exact match first
        cursor.execute("""
            SELECT ranking FROM owgr_rankings
            WHERE player_name = ?
        """, (player_name,))

        result = cursor.fetchone()

        if not result:
            # Normalize name for matching (replace special characters)
            # Nordic: å→a, ä→a, ö→o
            # Spanish: ñ→n, é→e, á→a, í→i
            # Other: ø→o
            normalized_name = (player_name
                .replace('å', 'a').replace('Å', 'A')
                .replace('ä', 'a').replace('Ä', 'A')
                .replace('ö', 'o').replace('Ö', 'O')
                .replace('ø', 'o').replace('Ø', 'O')
                .replace('ñ', 'n').replace('Ñ', 'N')
                .replace('é', 'e').replace('É', 'E')
                .replace('á', 'a').replace('Á', 'A')
                .replace('í', 'i').replace('Í', 'I')
                .replace('ó', 'o').replace('Ó', 'O')
                .replace('ú', 'u').replace('Ú', 'U'))

            # Try normalized exact match
            cursor.execute("""
                SELECT ranking FROM owgr_rankings
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                      REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    player_name,
                    'å', 'a'), 'Å', 'A'), 'ä', 'a'), 'Ä', 'A'), 'ö', 'o'), 'Ö', 'O'),
                    'ø', 'o'), 'Ø', 'O'), 'ñ', 'n'), 'Ñ', 'N'),
                    'é', 'e'), 'É', 'E'), 'á', 'a'), 'Á', 'A'), 'í', 'i'), 'Í', 'I'),
                    'ó', 'o'), 'Ó', 'O'), 'ú', 'u'), 'Ú', 'U') = ?
            """, (normalized_name,))
            result = cursor.fetchone()

        if not result:
            # Try name variations (e.g., Sam -> Samuel)
            parts = player_name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])

                # Try expanding shortened first name
                if first_name in name_variations:
                    full_first = name_variations[first_name]
                    full_name = f"{full_first} {last_name}"

                    cursor.execute("""
                        SELECT ranking FROM owgr_rankings
                        WHERE player_name = ?
                    """, (full_name,))
                    result = cursor.fetchone()

                # Try shortening full first name (reverse lookup)
                if not result:
                    for short, full in name_variations.items():
                        if first_name == full:
                            short_name = f"{short} {last_name}"
                            cursor.execute("""
                                SELECT ranking FROM owgr_rankings
                                WHERE player_name = ?
                            """, (short_name,))
                            result = cursor.fetchone()
                            if result:
                                break

        if not result:
            # Try name order reversal for two-part names only (e.g., "Min Woo Lee" -> "Lee Min Woo")
            # But ONLY if it's an exact match with just the order reversed
            parts = player_name.split()
            if len(parts) == 2:
                first_name = parts[0]
                last_name = parts[1]
                reversed_name = f"{last_name} {first_name}"

                # Try exact reversed match
                cursor.execute("""
                    SELECT ranking FROM owgr_rankings
                    WHERE player_name = ?
                """, (reversed_name,))
                result = cursor.fetchone()

        if not result:
            # Try partial match on BOTH first initial and last name to avoid false matches
            parts = player_name.split()
            if len(parts) >= 2:
                # Get first initial(s) - handle cases like "S.T." or "Min Woo"
                first_part = parts[0]
                last_name = parts[-1]

                # Extract first letter(s) for matching
                first_initial = first_part[0] if first_part else ''

                # Only match if first initial AND last name match
                # This prevents "S.T. Lee" from matching "Min Woo Lee"
                cursor.execute("""
                    SELECT ranking FROM owgr_rankings
                    WHERE player_name LIKE ?
                    AND player_name LIKE ?
                    LIMIT 1
                """, (f"{first_initial}%", f"%{last_name}"))
                result = cursor.fetchone()

        conn.close()

        return result[0] if result else None

    def save_tournament_par(self, tournament_id: str, year: int, par_data: dict):
        """Save tournament par information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create a composite key for tournament+year
        composite_id = f"{tournament_id}_{year}"

        cursor.execute("""
            INSERT OR REPLACE INTO tournaments
            (tournament_id, tournament_name, year, par_per_round, total_par, rounds, num_courses, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            composite_id,
            f"Tournament {tournament_id}",  # Placeholder name
            year,
            par_data.get('par_per_round'),
            par_data.get('total_par'),
            par_data.get('rounds'),
            par_data.get('num_courses'),
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def get_tournament_par(self, tournament_id: str, year: int) -> dict:
        """Get par information for a tournament"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        composite_id = f"{tournament_id}_{year}"

        try:
            # First, check if par columns exist and add them if not
            cursor.execute("PRAGMA table_info(tournaments)")
            existing_columns = [row[1] for row in cursor.fetchall()]

            par_columns_needed = ['par_per_round', 'total_par', 'rounds', 'num_courses']
            missing_columns = [col for col in par_columns_needed if col not in existing_columns]

            if missing_columns:
                # Add missing columns
                for col_name in missing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE tournaments ADD COLUMN {col_name} INTEGER")
                        conn.commit()
                    except Exception:
                        pass  # Column might already exist

            # Now query the par data
            cursor.execute("""
                SELECT par_per_round, total_par, rounds, num_courses
                FROM tournaments
                WHERE tournament_id = ?
            """, (composite_id,))

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                return {
                    'par_per_round': result[0],
                    'total_par': result[1],
                    'rounds': result[2],
                    'num_courses': result[3]
                }
        except Exception:
            # If query fails, return None
            try:
                conn.close()
            except:
                pass

        return None

    def get_tournaments(self) -> pd.DataFrame:
        """Retrieve all tournaments"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM tournaments ORDER BY start_date DESC", conn)
        conn.close()
        return df

    def get_tournament_results(self, tournament_id: str, year: int) -> pd.DataFrame:
        """Get results for a specific tournament and year"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT * FROM tournament_results
            WHERE tournament_id = ? AND year = ?
            ORDER BY CAST(position AS INTEGER)
        """
        df = pd.read_sql(query, conn, params=(tournament_id, year))
        conn.close()
        return df

    def get_player_tournament_history(self, player_name: str, tournament_id: str) -> pd.DataFrame:
        """Get a player's history at a specific tournament"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT * FROM tournament_results
            WHERE player_name LIKE ? AND tournament_id = ?
            ORDER BY year DESC
        """
        df = pd.read_sql(query, conn, params=(f"%{player_name}%", tournament_id))
        conn.close()
        return df

    def get_all_players_for_tournament(self, tournament_id: str) -> pd.DataFrame:
        """Get all unique players who have played in a tournament across all years"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT DISTINCT player_name, player_id
            FROM tournament_results
            WHERE tournament_id = ?
            ORDER BY player_name
        """
        df = pd.read_sql(query, conn, params=(tournament_id,))
        conn.close()
        return df

    def mark_player_used(self, player_name: str, tournament_name: str, week: str):
        """Mark a player as used in the one-and-done pool"""
        if self._current_user:
            from data.user_picks_store import mark_player_used
            mark_player_used(self._current_user, player_name, tournament_name, week)
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO used_players (player_name, tournament_name, week_used)
            VALUES (?, ?, ?)
        """, (player_name, tournament_name, week))
        conn.commit()
        conn.close()

    def get_used_players(self) -> List[str]:
        """Get list of all used players"""
        if self._current_user:
            from data.user_picks_store import get_used_players
            return get_used_players(self._current_user)
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT player_name FROM used_players", conn)
        conn.close()
        return df['player_name'].tolist() if not df.empty else []

    def get_used_players_details(self) -> pd.DataFrame:
        """Get detailed list of used players with tournament info"""
        if self._current_user:
            from data.user_picks_store import get_used_players_details
            return get_used_players_details(self._current_user)
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("""
            SELECT player_name, tournament_name, week_used, date_used
            FROM used_players
            ORDER BY date_used DESC
        """, conn)
        conn.close()
        return df

    def remove_used_player(self, player_name: str):
        """Remove a player from the used list"""
        if self._current_user:
            from data.user_picks_store import remove_used_player
            remove_used_player(self._current_user, player_name)
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM used_players WHERE player_name = ?", (player_name,))
        conn.commit()
        conn.close()

    def clear_used_players(self):
        """Clear all used players (start new season)"""
        if self._current_user:
            from data.user_picks_store import clear_used_players
            clear_used_players(self._current_user)
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM used_players")
        conn.commit()
        conn.close()

    def is_data_stale(self, table_name: str, max_age_days: int = 7) -> bool:
        """Check if cached data is stale"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(last_updated) FROM {table_name}")
        result = cursor.fetchone()
        conn.close()

        if result[0] is None:
            return True

        last_updated = datetime.fromisoformat(result[0])
        age = datetime.now() - last_updated
        return age > timedelta(days=max_age_days)
