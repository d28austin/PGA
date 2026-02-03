"""
Tournament History View Component
Shows all players' historical performance at a selected tournament
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime


def render_tournament_view(tournament_name, db, fetcher):
    """Render the tournament history analysis view"""

    st.subheader(f"📊 {tournament_name} - Historical Analysis")

    # Get all available years for this tournament (by name)
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    # Include ALL appearances (even missed cuts with position '-')
    cursor.execute("""
        SELECT DISTINCT year, tournament_id
        FROM tournament_results
        WHERE tournament_name = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY year DESC
    """, (tournament_name,))
    year_data = cursor.fetchall()
    conn.close()

    if not year_data:
        st.warning("No data available for this tournament.")
        return

    available_years = [row[0] for row in year_data]

    # Display available data info
    st.info(f"📊 Showing data for all {len(available_years)} year(s): {', '.join(map(str, available_years))}")

    # Use all available years
    selected_years = available_years

    st.divider()

    # Show results only (Analysis tab removed as it duplicates "In the Field" functionality)
    render_results_tab(tournament_name, db, available_years)


def render_results_tab(tournament_name, db, available_years):
    """Render the results tab showing tournament results by year"""

    import sqlite3

    # Year selector
    selected_year = st.selectbox(
        "Select Year:",
        options=sorted(available_years, reverse=True),
        help="View the leaderboard for a specific year"
    )

    if not selected_year:
        return

    st.divider()

    # Get tournament results for selected year
    conn = sqlite3.connect(db.db_path)
    # Include ALL appearances (even missed cuts with position '-')
    results_df = pd.read_sql("""
        SELECT player_name, position, total_score, earnings
        FROM tournament_results
        WHERE tournament_name = ? AND year = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY CAST(REPLACE(REPLACE(position, 'T', ''), 'T-', '') AS INTEGER)
    """, conn, params=(tournament_name, selected_year))
    conn.close()

    if results_df.empty:
        st.warning(f"No results available for {selected_year}")
        return

    # Get par info for this tournament/year
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT tournament_id
        FROM tournament_results
        WHERE tournament_name = ? AND year = ?
        LIMIT 1
    """, (tournament_name, selected_year))
    tournament_id_row = cursor.fetchone()
    conn.close()

    tournament_par = 288  # default
    if tournament_id_row:
        par_info = db.get_tournament_par(tournament_id_row[0], selected_year)
        if par_info:
            tournament_par = par_info['total_par']

    # Calculate score to par
    # Strip "T" prefix from tied positions before converting to numeric
    results_df['position_clean'] = results_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
    results_df['position_numeric'] = pd.to_numeric(results_df['position_clean'], errors='coerce')
    results_df['total_score_numeric'] = pd.to_numeric(results_df['total_score'], errors='coerce')

    # Determine made cut (position <= 70 and reasonable score - full 4 rounds)
    min_reasonable_score = tournament_par * 0.75
    results_df['made_cut'] = (results_df['position_numeric'] <= 70) & (results_df['total_score_numeric'] >= min_reasonable_score)

    # Calculate score to par - ONLY for players who made the cut
    results_df['score_to_par'] = results_df.apply(
        lambda row: row['total_score_numeric'] - tournament_par if row['made_cut'] else None,
        axis=1
    )

    # Format score to par display
    def format_score_to_par(score):
        if pd.isna(score):
            return ""
        score_int = int(score)
        if score_int == 0:
            return "E"
        elif score_int > 0:
            return f"+{score_int}"
        else:
            return str(score_int)

    results_df['score_to_par_display'] = results_df['score_to_par'].apply(format_score_to_par)

    # Keep numeric version for sorting
    results_df['score_to_par_numeric'] = results_df['score_to_par']

    # Format earnings but keep numeric for sorting
    results_df['earnings_numeric'] = pd.to_numeric(results_df['earnings'], errors='coerce').fillna(0)
    results_df['earnings_display'] = results_df['earnings_numeric'].apply(
        lambda x: f"${x:,.0f}" if x > 0 else ""
    )

    # For position sorting, replace NaN (from "-") with 999 so missed cuts sort to bottom
    results_df['position_sort'] = results_df['position_numeric'].fillna(999)

    # Check used players
    used_players = db.get_used_players()
    results_df['status'] = results_df['player_name'].apply(
        lambda x: "🚫 Used" if x in used_players else "✅ Available"
    )

    # Sort by position (1st place at top)
    results_df = results_df.sort_values('position_sort', ascending=True)

    # Display tournament info
    st.subheader(f"{tournament_name} - {selected_year} Results")
    st.caption(f"Tournament Par: {tournament_par}")
    st.caption(f"Total Players: {len(results_df)}")

    # Display leaderboard (hide helper sort columns)
    st.dataframe(
        results_df[['position', 'player_name', 'total_score', 'score_to_par_display', 'earnings_display', 'status']],
        column_config={
            "position": st.column_config.TextColumn("Pos", width="small", help="Finishing position (T = tied)"),
            "player_name": st.column_config.TextColumn("Player", width="medium"),
            "total_score": st.column_config.NumberColumn("Total", format="%d", help="Total strokes for the tournament"),
            "score_to_par_display": st.column_config.TextColumn("To Par", help="Score relative to par (E = even, - = under par)"),
            "earnings_display": st.column_config.TextColumn("Earnings", help="Prize money earned"),
            "status": st.column_config.TextColumn("Status", width="small")
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )
