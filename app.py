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
