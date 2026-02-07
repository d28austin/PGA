"""
PGA One-and-Done League Analyzer
Streamlit app for analyzing player performance and making weekly picks
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.espn_fetcher import ESPNPGAFetcher
from data.database import PGADatabase
from utils.tournament_names import get_tournament_name
from datetime import datetime

# Page config
st.set_page_config(
    page_title="PGA One-and-Done Analyzer",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mobile-responsive CSS — only activates on screens under 768px
st.markdown("""
<style>
@media only screen and (max-width: 768px) {
    /* Stack columns vertically instead of side-by-side */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        width: 100% !important;
        min-width: 100% !important;
    }

    /* Larger metric values and labels */
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }

    /* Make dataframes scroll smoothly */
    [data-testid="stDataFrame"] {
        -webkit-overflow-scrolling: touch;
    }

    /* Bigger tap targets for buttons and inputs */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
    }
    .stSelectbox, .stMultiSelect {
        font-size: 1rem !important;
    }

    /* Reduce excessive padding */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Make subheaders slightly smaller to save space */
    h2 {
        font-size: 1.3rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = PGADatabase()
if 'fetcher' not in st.session_state:
    st.session_state.fetcher = ESPNPGAFetcher()
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False


def load_initial_data():
    """Load tournament schedule and basic data"""
    with st.spinner("Loading 2026 tournament data..."):
        calendar = st.session_state.fetcher.get_season_calendar(2026)
        if calendar:
            import pandas as pd
            schedule = pd.DataFrame(calendar)
            schedule['tournament_id'] = schedule['event_id']
            schedule['tournament_name'] = schedule['name']
            schedule['year'] = 2026
            st.session_state.db.save_tournaments(schedule)
            st.session_state.data_loaded = True
            return True
        return False


def main():
    # Title and header
    st.title("⛳ PGA One-and-Done League Analyzer")
    st.markdown("Analyze player performance and tournament history to make informed weekly picks")

    # Sidebar
    with st.sidebar:
        st.header("Settings & Filters")

        # Load data if not already loaded
        if not st.session_state.data_loaded:
            load_initial_data()

        # Show last updated timestamps
        try:
            import sqlite3 as _sqlite3
            from datetime import datetime as _dt
            _conn = _sqlite3.connect(st.session_state.db.db_path)
            _cur = _conn.cursor()
            _cur.execute("SELECT MAX(last_updated) FROM tournament_results")
            _data_updated = _cur.fetchone()[0]
            _cur.execute("SELECT MAX(last_updated) FROM owgr_rankings")
            _owgr_updated = _cur.fetchone()[0]
            _conn.close()

            if _data_updated:
                _dt_parsed = _dt.fromisoformat(str(_data_updated).replace('T', ' ').split('.')[0])
                st.caption(f"Data last updated: {_dt_parsed.strftime('%b %d, %Y %I:%M %p')}")
            if _owgr_updated:
                _owgr_parsed = _dt.fromisoformat(str(_owgr_updated).replace('T', ' ').split('.')[0])
                st.caption(f"OWGR last updated: {_owgr_parsed.strftime('%b %d, %Y %I:%M %p')}")
        except Exception:
            pass

        # App last updated from git commit or file modification
        try:
            import os
            _app_mtime = os.path.getmtime(os.path.abspath(__file__))
            _app_dt = _dt.fromtimestamp(_app_mtime)
            st.caption(f"App last updated: {_app_dt.strftime('%b %d, %Y %I:%M %p')}")
        except Exception:
            pass

        # Update Data expander
        with st.expander("Update Data"):
            if st.button("Update Tournament Results", use_container_width=True):
                fetcher = st.session_state.fetcher
                db = st.session_state.db

                status_text = st.empty()
                progress_bar = st.progress(0)

                status_text.text("Fetching 2026 calendar...")
                calendar = fetcher.get_season_calendar(2026)

                if not calendar:
                    status_text.text("Failed to fetch calendar.")
                else:
                    # Filter to completed tournaments
                    now = _dt.now()
                    completed = []
                    for event in calendar:
                        end_date_str = event.get('end_date')
                        if end_date_str:
                            try:
                                end_date = _dt.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                if end_date < now:
                                    completed.append(event)
                            except (ValueError, TypeError):
                                pass

                    # Find which tournaments already have results in the DB
                    import sqlite3 as _sq
                    _conn2 = _sq.connect(db.db_path)
                    existing_ids = set(
                        r[0] for r in _conn2.execute(
                            "SELECT DISTINCT tournament_id FROM tournament_results WHERE year = 2026"
                        ).fetchall()
                    )
                    _conn2.close()

                    missing = [e for e in completed if e['event_id'] not in existing_ids]

                    if not missing:
                        status_text.text("All completed tournaments are up to date.")
                        progress_bar.progress(1.0)
                    else:
                        import time
                        total_players = 0
                        updated_count = 0

                        for idx, event in enumerate(missing):
                            event_id = event['event_id']
                            name = event.get('name', event_id)
                            status_text.text(f"Fetching {name}... ({idx + 1}/{len(missing)})")
                            progress_bar.progress((idx) / len(missing))

                            results_df = fetcher.get_tournament_results(event_id, 2026)
                            if not results_df.empty:
                                db.save_tournament_results(results_df)
                                total_players += len(results_df)
                                updated_count += 1

                            par_data = fetcher.get_tournament_par(event_id)
                            if par_data:
                                db.save_tournament_par(event_id, 2026, par_data)

                            if idx < len(missing) - 1:
                                time.sleep(2)

                        progress_bar.progress(1.0)
                        status_text.text(
                            f"Done! Updated {updated_count} tournaments, {total_players} player results."
                        )
                        time.sleep(2)
                        st.rerun()

            if st.button("Update OWGR Rankings", use_container_width=True):
                import glob as _glob
                import os as _os
                import csv as _csv

                db = st.session_state.db
                owgr_status = st.empty()

                # Find the most recent downloaded_rankings CSV in the repo
                app_dir = _os.path.dirname(_os.path.abspath(__file__))
                csv_files = _glob.glob(_os.path.join(app_dir, "downloaded_rankings*.csv"))

                if not csv_files:
                    owgr_status.warning("No downloaded_rankings*.csv file found in the project folder. "
                                        "Download the CSV from owgr.com and place it here.")
                else:
                    # Pick the most recently modified file
                    latest_csv = max(csv_files, key=_os.path.getmtime)
                    file_mod_time = _dt.fromtimestamp(_os.path.getmtime(latest_csv))
                    owgr_status.text(f"Reading {_os.path.basename(latest_csv)} (modified {file_mod_time.strftime('%b %d, %Y')})...")

                    rankings = {}
                    weekend_date = None
                    with open(latest_csv, 'r', encoding='utf-8-sig') as f:
                        reader = _csv.DictReader(f)
                        for row in reader:
                            try:
                                first = row.get('First Name', '').strip().strip('"')
                                last = row.get('Last Name', '').strip().strip('"')
                                rank_str = row.get('RANKING', '').strip().strip('"')
                                if first and last and rank_str:
                                    rank = int(rank_str)
                                    if rank > 0:
                                        player_name = f"{first} {last}"
                                        rankings[player_name] = rank
                                if not weekend_date:
                                    weekend_date = row.get('Weekend date', '').strip().strip('"')
                            except (ValueError, TypeError):
                                continue

                    if rankings:
                        # Full replace — the CSV has the complete ranking list
                        import sqlite3 as _sq2
                        conn = _sq2.connect(db.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS owgr_rankings (
                                player_name TEXT PRIMARY KEY,
                                ranking INTEGER NOT NULL,
                                last_updated TEXT NOT NULL
                            )
                        """)
                        # Ensure player_aliases table exists for name matching
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS player_aliases (
                                alias_name TEXT PRIMARY KEY,
                                official_name TEXT NOT NULL,
                                notes TEXT
                            )
                        """)
                        # Seed known aliases if table is empty
                        cursor.execute("SELECT COUNT(*) FROM player_aliases")
                        if cursor.fetchone()[0] == 0:
                            _aliases = [
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
                            for alias, official, notes in _aliases:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO player_aliases
                                    (alias_name, official_name, notes)
                                    VALUES (?, ?, ?)
                                """, (alias, official, notes))
                        cursor.execute("DELETE FROM owgr_rankings")
                        timestamp = _dt.now().isoformat()
                        for pname, rank in rankings.items():
                            cursor.execute("""
                                INSERT INTO owgr_rankings
                                (player_name, ranking, last_updated)
                                VALUES (?, ?, ?)
                            """, (pname, rank, timestamp))
                        conn.commit()
                        conn.close()

                        date_label = weekend_date if weekend_date else file_mod_time.strftime('%b %d, %Y')
                        owgr_status.text(
                            f"Loaded {len(rankings)} OWGR rankings (week of {date_label}) "
                            f"from {_os.path.basename(latest_csv)}"
                        )
                        import time as _time
                        _time.sleep(2)
                        st.rerun()
                    else:
                        owgr_status.warning("No valid rankings found in the CSV file.")

            if st.button("Refresh Tournament Field", use_container_width=True):
                from utils.fetch_tournament_field import fetch_field_by_tournament_id
                import sqlite3 as _sq3

                field_status = st.empty()
                field_status.text("Finding upcoming tournament...")

                _conn3 = _sq3.connect(st.session_state.db.db_path)
                _cur3 = _conn3.cursor()

                # Find the next upcoming (or most recent) tournament from 2026 schedule
                _cur3.execute("""
                    SELECT tournament_name, tournament_id, date
                    FROM tournament_2026_ids
                    WHERE date >= date('now', '-5 days')
                    ORDER BY date ASC
                    LIMIT 1
                """)
                upcoming = _cur3.fetchone()
                _conn3.close()

                if upcoming:
                    t_name, t_id, t_date = upcoming
                    field_status.text(f"Fetching field for {t_name}...")
                    field = fetch_field_by_tournament_id(t_id)
                    if field:
                        # Cache in session state so field_view can use it
                        st.session_state.cached_field = {
                            'tournament_name': t_name,
                            'tournament_id': t_id,
                            'players': field,
                        }
                        field_status.success(
                            f"**{t_name}** — {len(field)} players in field. "
                            f"Go to 'In the Field' tab to analyze."
                        )
                    else:
                        field_status.warning(
                            f"**{t_name}** — Field not yet published on ESPN. "
                            f"Check back Tuesday/Wednesday."
                        )
                else:
                    field_status.warning("No upcoming tournament found in the 2026 schedule.")

        st.divider()

        # Tournament selectors - two options: alphabetical or by date
        st.subheader("Select Tournament")

        import sqlite3
        conn = sqlite3.connect(st.session_state.db.db_path)

        # Get 2026 calendar tournaments ordered by date
        calendar_2026_df = None
        try:
            calendar_query = """
                SELECT tournament_name, date, status
                FROM tournament_2026_ids
                ORDER BY date
            """
            calendar_2026_df = pd.read_sql(calendar_query, conn)
        except:
            pass  # Table might not exist

        # Get historical tournaments alphabetically
        history_query = """
            SELECT DISTINCT
                tournament_name,
                COUNT(DISTINCT year) as year_count,
                MIN(year) as first_year,
                MAX(year) as last_year,
                COUNT(*) as total_player_results
            FROM tournament_results
            WHERE tournament_name IS NOT NULL
                AND tournament_name != ''
                AND tournament_id != 'T001'
                AND CAST(position AS INTEGER) > 0
            GROUP BY tournament_name
            ORDER BY tournament_name
        """
        tournaments_df = pd.read_sql(history_query, conn)
        conn.close()

        # Create two selection methods
        selection_method = st.radio(
            "Choose selection method:",
            ["📅 2026 Schedule (by date)", "📚 All Tournaments (alphabetical)"],
            horizontal=True
        )

        selected_tournament_name = None

        if selection_method == "📅 2026 Schedule (by date)" and calendar_2026_df is not None and not calendar_2026_df.empty:
            # Format date and create display options
            from datetime import datetime, timedelta

            calendar_2026_df['date_parsed'] = pd.to_datetime(calendar_2026_df['date'], utc=True)
            # Remove timezone info by converting to naive datetime for comparison
            calendar_2026_df['date_parsed_naive'] = calendar_2026_df['date_parsed'].dt.tz_localize(None)
            calendar_2026_df['date_display'] = calendar_2026_df['date_parsed'].dt.strftime('%b %d')

            # Filter out tournaments that ended more than 5 days ago
            now = datetime.now()
            cutoff_date = now - timedelta(days=5)

            # Keep tournaments that are either upcoming or ended within last 5 days
            calendar_2026_df = calendar_2026_df[calendar_2026_df['date_parsed_naive'] >= cutoff_date].copy()

            if calendar_2026_df.empty:
                st.warning("No upcoming tournaments in 2026 schedule. Use 'All Tournaments' view.")
                selected_tournament_name = None
            else:
                # Create display with date, name, and status
                calendar_options = calendar_2026_df.apply(
                    lambda x: f"{x['date_display']} - {x['tournament_name']}" +
                             (f" ({x['status']})" if x['status'] not in ['Scheduled', 'Final'] else ""),
                    axis=1
                ).tolist()

                selected_calendar = st.selectbox(
                    "2026 PGA Tour Schedule:",
                    options=calendar_options,
                    help="Tournaments ordered by date in 2026 (shows upcoming and recent events only)"
                )

                if selected_calendar:
                    idx = calendar_options.index(selected_calendar)
                    selected_tournament_name = calendar_2026_df.iloc[idx]['tournament_name']

        else:
            # Show alphabetical historical selector
            if not tournaments_df.empty:
                tournament_options = tournaments_df.apply(
                    lambda x: f"{x['tournament_name']} ({x['year_count']} years: {x['first_year']}-{x['last_year']})"
                    if x['year_count'] > 1
                    else f"{x['tournament_name']} ({x['first_year']})",
                    axis=1
                ).tolist()

                selected_tournament = st.selectbox(
                    "All Tournaments (A-Z):",
                    options=tournament_options,
                    help="Choose a tournament to analyze - shows all available years"
                )

                if selected_tournament:
                    idx = tournament_options.index(selected_tournament)
                    selected_tournament_name = tournaments_df.iloc[idx]['tournament_name']
            else:
                st.warning("No tournament data available. Run the data loader script:")
                st.code("python quick_load_sample_data.py")

        # Update session state with selected tournament
        if selected_tournament_name:
            st.session_state.current_tournament_name = selected_tournament_name
            # Get year count for this tournament
            matching = tournaments_df[tournaments_df['tournament_name'] == selected_tournament_name]
            if not matching.empty:
                st.session_state.current_year_count = matching.iloc[0]['year_count']
            else:
                st.session_state.current_year_count = 1
        else:
            st.session_state.current_tournament_name = None

        st.divider()

        # Used players section
        st.subheader("One-and-Done Tracker")
        used_players = st.session_state.db.get_used_players()

        if used_players:
            st.info(f"🚫 {len(used_players)} player(s) already used")
            if st.button("View Used Players"):
                st.session_state.show_used_players = True
        else:
            st.success("No players used yet this season")

        if st.button("Clear All Used Players", use_container_width=True):
            st.session_state.db.clear_used_players()
            st.rerun()

    # Main content area with tabs
    tab0, tab1, tab2, tab3, tab4, tab_schedule, tab_players, tab_stats = st.tabs([
        "🏌️ In the Field",
        "📊 Tournament History",
        "👤 Player Deep Dive",
        "📈 Recent Form",
        "💰 Betting Odds",
        "📅 2026 Schedule",
        "👥 All Players",
        "🎯 ESPN Stats"
    ])

    with tab0:
        st.header("Players in the Field")
        if hasattr(st.session_state, 'current_tournament_name') and st.session_state.current_tournament_name:
            from components.field_view import render_field_view
            render_field_view(
                st.session_state.current_tournament_name,
                st.session_state.db,
                st.session_state.fetcher
            )
        else:
            st.info("Please select a tournament from the sidebar")

    with tab1:
        st.header("Tournament History Analysis")
        if hasattr(st.session_state, 'current_tournament_name') and st.session_state.current_tournament_name:
            from components.tournament_view import render_tournament_view
            render_tournament_view(
                st.session_state.current_tournament_name,
                st.session_state.db,
                st.session_state.fetcher
            )
        else:
            st.info("Please select a tournament from the sidebar")

    with tab2:
        st.header("Player Deep Dive")
        if hasattr(st.session_state, 'current_tournament_name') and st.session_state.current_tournament_name:
            from components.player_view import render_player_view
            render_player_view(
                st.session_state.current_tournament_name,
                st.session_state.db,
                st.session_state.fetcher
            )
        else:
            st.info("Please select a tournament from the sidebar")

    with tab3:
        st.header("Recent Form Analysis")
        from components.recent_form import render_recent_form
        render_recent_form(st.session_state.db)

    with tab4:
        if hasattr(st.session_state, 'current_tournament_name') and st.session_state.current_tournament_name:
            from components.recommendations import render_recommendations
            render_recommendations(
                st.session_state.current_tournament_name,
                st.session_state.db,
                st.session_state.fetcher
            )
        else:
            st.info("Please select a tournament from the sidebar")

    with tab_schedule:
        from components.schedule_view import render_schedule_view
        render_schedule_view(st.session_state.db)

    with tab_players:
        from components.player_management import render_player_management
        render_player_management(st.session_state.db)

    with tab_stats:
        from components.player_stats_view import render_player_stats_view
        render_player_stats_view(st.session_state.db)

    # Show used players modal if requested
    if hasattr(st.session_state, 'show_used_players') and st.session_state.show_used_players:
        with st.expander("Used Players Details", expanded=True):
            used_df = st.session_state.db.get_used_players_details()
            if not used_df.empty:
                st.dataframe(used_df, use_container_width=True)

                # Option to remove individual players
                player_to_remove = st.selectbox("Remove a player:", [""] + used_df['player_name'].tolist())
                if player_to_remove and st.button("Remove Selected Player"):
                    st.session_state.db.remove_used_player(player_to_remove)
                    st.session_state.show_used_players = False
                    st.rerun()
            else:
                st.info("No players have been used yet")

            if st.button("Close"):
                st.session_state.show_used_players = False
                st.rerun()


if __name__ == "__main__":
    main()
