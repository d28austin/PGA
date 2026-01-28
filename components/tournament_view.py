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

    # Create sub-tabs for Analysis and Results
    tab_analysis, tab_results = st.tabs(["Analysis", "Results"])

    with tab_analysis:
        render_analysis_tab(tournament_name, db, year_data, selected_years)

    with tab_results:
        render_results_tab(tournament_name, db, available_years)


def render_analysis_tab(tournament_name, db, year_data, selected_years):
    """Render the analysis tab with aggregated statistics"""

    import sqlite3

    # Load tournament results by name (all years)
    conn = sqlite3.connect(db.db_path)
    # Include ALL appearances (even missed cuts with position '-')
    combined_df = pd.read_sql("""
        SELECT *
        FROM tournament_results
        WHERE tournament_name = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY year DESC,
                 CAST(REPLACE(REPLACE(position, 'T', ''), 'T-', '') AS INTEGER)
    """, conn, params=(tournament_name,))
    conn.close()

    if combined_df.empty:
        st.warning("No data loaded for this tournament.")
        return

    # Filter options
    st.subheader("Filter Players")
    col1, col2 = st.columns(2)

    with col1:
        # Filter by used players
        hide_used = st.checkbox("Hide already used players", value=True)
        if hide_used:
            used_players = db.get_used_players()
            combined_df = combined_df[~combined_df['player_name'].isin(used_players)]

    with col2:
        # Filter by minimum appearances - default to 1
        max_possible = combined_df.groupby('player_name').size().max()
        if max_possible > 1:
            min_appearances = st.slider("Minimum tournament appearances", 1, int(max_possible), 1)
        else:
            min_appearances = 1
            st.caption(f"All players have 1 appearance")

    # Convert position and score to numeric BEFORE aggregation
    # Strip "T" prefix from tied positions before converting to numeric
    combined_df['position_clean'] = combined_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
    combined_df['position_numeric'] = pd.to_numeric(combined_df['position_clean'], errors='coerce')
    combined_df['total_score_numeric'] = pd.to_numeric(combined_df['total_score'], errors='coerce')
    combined_df['earnings_numeric'] = pd.to_numeric(combined_df['earnings'], errors='coerce')

    # Get actual par from database
    # Get par for each year using the tournament_id
    par_info_map = {}
    for year, tournament_id in year_data:
        par_info = db.get_tournament_par(tournament_id, year)
        if par_info:
            par_info_map[year] = par_info

    # Use the most recent year's par, or first available
    if par_info_map:
        most_recent_year = max(par_info_map.keys())
        par_info = par_info_map[most_recent_year]
        tournament_par = par_info['total_par']
        rounds_played = par_info['rounds']
        par_per_round = par_info['par_per_round']
    else:
        # Fallback to estimation if no par data available
        tournament_par = 288
        rounds_played = 4
        par_per_round = 72

    # Calculate score relative to par
    combined_df['score_to_par'] = combined_df['total_score_numeric'] - tournament_par

    # Mark which entries made the cut (position <= 70 and score is reasonable)
    # A reasonable score is at least 75% of tournament par (e.g., at least 216 for par 288)
    min_reasonable_score = tournament_par * 0.75
    combined_df['made_cut'] = (combined_df['position_numeric'] <= 70) & (combined_df['total_score_numeric'] >= min_reasonable_score)

    # Helper function to calculate stats
    def calculate_top_10s(positions):
        """Count number of top 10 finishes"""
        return (positions <= 10).sum()

    def calculate_made_cuts(positions):
        """Count number of times made the cut (finished the tournament)"""
        # In PGA Tour, typically top 70 make the cut and earn money
        return (positions <= 70).sum()

    def calculate_avg_score_made_cuts(df_subset):
        """Calculate average score only for rounds where player made the cut"""
        made_cut_scores = df_subset[df_subset['made_cut']]['score_to_par']
        if len(made_cut_scores) > 0:
            return made_cut_scores.mean()
        return None

    # Calculate summary statistics per player
    player_stats = combined_df.groupby('player_name').agg({
        'year': 'count',  # Count ALL appearances including missed cuts
        'position_numeric': ['mean', 'min', calculate_top_10s, calculate_made_cuts],
        'earnings_numeric': 'sum'
    }).reset_index()

    # Calculate average score separately (only for made cuts)
    avg_scores = combined_df.groupby('player_name').apply(calculate_avg_score_made_cuts).reset_index()
    avg_scores.columns = ['player_name', 'avg_score_to_par']

    # Set proper column names before merge
    player_stats.columns = ['player_name', 'appearances', 'avg_finish', 'best_finish', 'top_10s', 'made_cuts', 'total_earnings']

    # Merge the scores back
    player_stats = player_stats.merge(avg_scores, on='player_name', how='left')

    player_stats = player_stats[player_stats['appearances'] >= min_appearances]
    player_stats = player_stats.sort_values('avg_finish')

    # avg_finish is already numeric
    player_stats['avg_finish_numeric'] = player_stats['avg_finish']

    # Add OWGR data from database - create both numeric (for sorting) and display versions
    player_stats['owgr_numeric'] = player_stats['player_name'].apply(
        lambda name: db.get_player_owgr(name) if db.get_player_owgr(name) else 9999
    )
    player_stats['owgr'] = player_stats['owgr_numeric'].apply(
        lambda x: str(int(x)) if x < 9999 else 'NR'
    )

    # Calculate Value metric: (Made_Cuts + Top10s * 3) * 10 / OWGR
    # This rewards consistency and quality finishes relative to world ranking
    # Scaled by 10 to produce values similar to reference (typically 2-15 range)
    def calculate_value_numeric(row):
        owgr = row['owgr_numeric']
        if owgr >= 9999:
            return 0  # NR players get 0 value
        try:
            made_cuts = row['made_cuts']
            top10s = row['top_10s']
            # Performance score: made cuts + top10s weighted 3x
            performance = made_cuts + (top10s * 3)
            # Value = performance relative to ranking, scaled for readability
            value = (performance * 10) / owgr
            return round(value, 2)
        except:
            return 0

    player_stats['value_numeric'] = player_stats.apply(calculate_value_numeric, axis=1)
    player_stats['value'] = player_stats['value_numeric'].apply(
        lambda x: str(x) if x > 0 else 'NR'
    )

    # Display summary table
    st.subheader(f"Top Performers at {tournament_name}")
    st.caption(f"Showing players with at least {min_appearances} appearances | Course Par: {tournament_par} ({rounds_played} rounds × {par_per_round}) | Avg Score: Made cuts only")

    # Format the display dataframe
    display_df = player_stats.copy()
    # Replace None in avg_finish with 999 so it sorts to bottom
    display_df['avg_finish'] = display_df['avg_finish_numeric'].fillna(999).round(1)
    display_df['best_finish'] = display_df['best_finish'].astype('Int64')
    display_df['total_earnings'] = display_df['total_earnings'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else "N/A")

    # Keep numeric column for sorting - use rounded values, replace NaN with empty string for display
    display_df['avg_score_sortable'] = display_df['avg_score_to_par'].round(0)

    display_df['made_cut_pct'] = (display_df['made_cuts'] / display_df['appearances'] * 100).round(0).astype('Int64')

    # Function to format with +/- prefix for display
    def format_number_with_sign(value):
        if pd.isna(value):
            return None  # Will show as empty, sorts to bottom
        value_int = int(value)
        if value_int > 0:
            return f"+{value_int}"
        elif value_int == 0:
            return "E"
        else:
            return str(value_int)

    st.dataframe(
        display_df[['player_name', 'appearances', 'avg_finish', 'best_finish', 'top_10s', 'made_cuts', 'made_cut_pct', 'avg_score_sortable', 'owgr_numeric', 'value_numeric']],
        column_config={
            "player_name": "Player",
            "appearances": st.column_config.NumberColumn("Apps", format="%d", help="Number of times played this tournament"),
            "avg_finish": st.column_config.NumberColumn("Avg Finish", format="%.1f", help="Average finishing position"),
            "best_finish": st.column_config.NumberColumn("Best", format="%d", help="Best finish at this tournament"),
            "top_10s": st.column_config.NumberColumn("Top 10s", format="%d", help="Number of top 10 finishes"),
            "made_cuts": st.column_config.NumberColumn("Made Cut", format="%d", help="Times finished in top 70 (made the cut)"),
            "made_cut_pct": st.column_config.NumberColumn("Cut %", format="%d%%", help="Percentage of times made the cut"),
            "avg_score_sortable": st.column_config.NumberColumn(
                "Avg Score",
                format="%d",
                help="Average score relative to par for made cuts only. Negative is under par (better). Click to sort - lowest scores at top."
            ),
            "owgr_numeric": st.column_config.NumberColumn("OWGR", format="%d", help="Official World Golf Ranking (9999 = Not Ranked)"),
            "value_numeric": st.column_config.NumberColumn("Value", format="%.2f", help="Performance value relative to world ranking (Higher = Better value pick, 0 = Not Ranked)")
        },
        hide_index=True,
        use_container_width=True
    )

    # Visualization section
    st.divider()
    st.subheader("Visualizations")

    tab1, tab2 = st.tabs(["Top Performers Chart", "Year-by-Year Results"])

    with tab1:
        # Top 10 players by average finish
        top_10 = player_stats.nsmallest(10, 'avg_finish_numeric')

        fig = px.bar(
            top_10,
            x='player_name',
            y='avg_finish_numeric',
            title=f'Top 10 Players by Average Finish at {tournament_name}',
            labels={'player_name': 'Player', 'avg_finish_numeric': 'Average Finish Position'},
            color='avg_finish_numeric',
            color_continuous_scale='RdYlGn_r'
        )
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Select a player to view year-by-year
        selected_player = st.selectbox(
            "Select a player to view history:",
            options=sorted(combined_df['player_name'].unique())
        )

        if selected_player:
            player_history = combined_df[combined_df['player_name'] == selected_player].sort_values('year')

            # position_numeric already exists from earlier cleaning (line 103)

            fig2 = px.line(
                player_history,
                x='year',
                y='position_numeric',
                title=f"{selected_player}'s Performance at {tournament_name}",
                labels={'year': 'Year', 'position_numeric': 'Finish Position'},
                markers=True
            )
            fig2.update_yaxes(autorange='reversed')  # Lower position is better
            st.plotly_chart(fig2, use_container_width=True)

            # Show detailed results table
            st.dataframe(
                player_history[['year', 'position', 'total_score', 'earnings']],
                column_config={
                    "year": st.column_config.NumberColumn("Year", format="%d"),
                    "position": "Position",
                    "total_score": "Score",
                    "earnings": st.column_config.NumberColumn("Earnings", format="$%d")
                },
                hide_index=True,
                use_container_width=True
            )

    # Mark player as used button
    st.divider()
    st.subheader("Mark Player as Used")
    col1, col2 = st.columns([3, 1])

    with col1:
        player_to_mark = st.selectbox(
            "Select player to mark as used:",
            options=[""] + sorted(combined_df['player_name'].unique())
        )

    with col2:
        if player_to_mark and st.button("Mark as Used", use_container_width=True):
            db.mark_player_used(player_to_mark, tournament_name, f"Week {datetime.now().isocalendar()[1]}")
            st.success(f"✅ Marked {player_to_mark} as used")
            st.rerun()


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

    # Display tournament info
    st.subheader(f"{tournament_name} - {selected_year} Results")
    st.caption(f"Tournament Par: {tournament_par}")
    st.caption(f"Total Players: {len(results_df)}")

    # Display leaderboard
    st.dataframe(
        results_df[['position', 'position_sort', 'player_name', 'total_score', 'score_to_par_display', 'score_to_par_numeric', 'earnings_display', 'earnings_numeric', 'status']],
        column_config={
            "position": st.column_config.TextColumn("Pos", width="small"),
            "position_sort": st.column_config.NumberColumn("Pos #", help="Numeric position for sorting (999 = missed cut)"),
            "player_name": st.column_config.TextColumn("Player", width="medium"),
            "total_score": st.column_config.NumberColumn("Total", format="%d", help="Total strokes"),
            "score_to_par_display": st.column_config.TextColumn("To Par", help="Score relative to par (made cuts only)"),
            "score_to_par_numeric": st.column_config.NumberColumn("To Par #", format="%d", help="Numeric score for sorting"),
            "earnings_display": st.column_config.TextColumn("Earnings", help="Prize money earned"),
            "earnings_numeric": st.column_config.NumberColumn("Earnings $", format="$%.0f", help="Numeric earnings for sorting"),
            "status": st.column_config.TextColumn("Status", width="small")
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )
