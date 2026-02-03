"""
Tournament Field View Component
Shows analysis for players in the current tournament field
Uses unified ValueCalculator with regression-optimized weights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from utils.fetch_tournament_field import fetch_tournament_field, fetch_field_by_tournament_id
from datetime import datetime
from components.value_calculator import ValueCalculator


def render_field_view(tournament_name, db, fetcher):
    """Render the tournament field analysis view"""

    st.subheader(f"🏌️ Players in the Field - {tournament_name}")

    # Try to fetch current field from ESPN
    with st.spinner("Fetching current tournament field from ESPN..."):
        field_players = []
        tournament_id_used = None
        field_year = None  # Track which year the field is from

        # Strategy 1: Check our 2026 tournament ID table
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Check if tournament_2026_ids table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='tournament_2026_ids'
        """)

        if cursor.fetchone():
            # Try exact match first
            cursor.execute("""
                SELECT tournament_id, tournament_name
                FROM tournament_2026_ids
                WHERE LOWER(tournament_name) = LOWER(?)
            """, (tournament_name,))
            result = cursor.fetchone()

            if result:
                tournament_id = result[0]
                found_name = result[1]
                st.info(f"Found 2026 tournament: {found_name} (ID: {tournament_id})")
                field_players = fetch_field_by_tournament_id(tournament_id)
                if field_players:
                    tournament_id_used = tournament_id
                    field_year = 2026

            # Try partial match if exact didn't work
            if not field_players:
                cursor.execute("""
                    SELECT tournament_id, tournament_name
                    FROM tournament_2026_ids
                    WHERE LOWER(tournament_name) LIKE LOWER(?)
                    OR LOWER(?) LIKE LOWER(tournament_name)
                    LIMIT 1
                """, (f'%{tournament_name}%', f'%{tournament_name}%'))
                result = cursor.fetchone()

                if result:
                    tournament_id = result[0]
                    found_name = result[1]
                    st.info(f"Found similar 2026 tournament: {found_name} (ID: {tournament_id})")
                    field_players = fetch_field_by_tournament_id(tournament_id)
                    if field_players:
                        tournament_id_used = tournament_id
                        field_year = 2026

        conn.close()

        # Strategy 2: If not found in 2026 table, offer manual entry or fall back to historical data
        if not field_players:
            st.warning(f"⚠️ 2026 field not yet available from schedule")

            # Option to manually enter 2026 tournament ID
            with st.expander("🔧 Manual Entry - Try 2026 Tournament ID", expanded=False):
                st.markdown("If you know the 2026 ESPN tournament ID, enter it here to check if the field has been published:")
                manual_2026_id = st.text_input("2026 ESPN Tournament ID:", key="manual_2026_id", placeholder="e.g., 401811932")

                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Fetch 2026 Field", use_container_width=True):
                        if manual_2026_id:
                            test_field = fetch_field_by_tournament_id(manual_2026_id)
                            if test_field:
                                field_players = test_field
                                tournament_id_used = manual_2026_id
                                field_year = 2026
                                st.success(f"✅ Found {len(field_players)} players in 2026 field!")
                                st.rerun()
                            else:
                                st.error("No field data available for this ID yet")
                        else:
                            st.error("Please enter a tournament ID")

            # Strategy 3: Fall back to showing historical field as reference
            if not field_players:
                st.info("Showing most recent historical field as reference...")

                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT tournament_id, year
                    FROM tournament_results
                    WHERE tournament_name = ?
                    AND year >= 2025
                    ORDER BY year DESC
                    LIMIT 1
                """, (tournament_name,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    tournament_id = result[0]
                    year = result[1]
                    field_players = fetch_field_by_tournament_id(tournament_id)
                    if field_players:
                        tournament_id_used = tournament_id
                        field_year = year

        if not field_players:
            st.warning("⚠️ Could not fetch current tournament field from ESPN")
            st.info("This feature requires an active tournament with a published field")
            st.markdown("**Manual Entry:** If you know the ESPN tournament ID, you can enter it below:")

            manual_id = st.text_input("ESPN Tournament ID (e.g., 401811930):")
            if manual_id and st.button("Fetch Field"):
                field_players = fetch_field_by_tournament_id(manual_id)
                if field_players:
                    tournament_id_used = manual_id
                    st.success(f"✅ Found {len(field_players)} players!")
                    st.rerun()
                else:
                    st.error("Could not fetch field with that ID")

            if not field_players:
                return

    # Show appropriate success message based on field year
    if field_year == 2026:
        st.success(f"✅ Found {len(field_players)} players in the current 2026 field")
    else:
        st.info(f"📋 Showing {len(field_players)} players from {field_year} field (2026 field not yet published)")

    st.divider()

    # Calculate tournament purse and ranking
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Strategy 1: Try to get purse from 2026 schedule (official data)
    tournament_purse = 0
    purse_year = "2026"

    cursor.execute("""
        SELECT purse
        FROM tournament_2026_ids
        WHERE tournament_name = ?
        AND purse > 0
    """, (tournament_name,))
    result = cursor.fetchone()

    if result:
        tournament_purse = result[0]
    else:
        # Strategy 2: Fall back to calculating from most recent earnings data
        purse_df = pd.read_sql("""
            SELECT
                year,
                SUM(earnings) as total_purse
            FROM tournament_results
            WHERE tournament_name = ?
            AND earnings > 0
            GROUP BY year
            ORDER BY year DESC
            LIMIT 1
        """, conn, params=(tournament_name,))

        if not purse_df.empty and purse_df['total_purse'].iloc[0] > 0:
            tournament_purse = purse_df['total_purse'].iloc[0]
            purse_year = str(purse_df['year'].iloc[0])

    # Get all 2026 tournament purses to rank them
    all_purses_df = pd.read_sql("""
        SELECT
            tournament_name,
            purse as total_purse
        FROM tournament_2026_ids
        WHERE purse > 0
        ORDER BY purse DESC
    """, conn)

    conn.close()

    # Display purse information
    if tournament_purse > 0:
        # Find rank (number of tournaments with higher purse + 1)
        purse_rank = (all_purses_df['total_purse'] > tournament_purse).sum() + 1

        # Count how many tournaments share this purse (for ties)
        tied_count = (all_purses_df['total_purse'] == tournament_purse).sum()

        total_tournaments = len(all_purses_df)

        st.subheader("💰 Tournament Purse Information")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Purse",
                f"${tournament_purse:,.0f}",
                help=f"Based on {purse_year} data"
            )

        with col2:
            # Format rank with tie notation if applicable
            if tied_count > 1:
                rank_display = f"T-{purse_rank} ({tied_count}) of {total_tournaments}"
            else:
                rank_display = f"#{purse_rank} of {total_tournaments}"

            st.metric(
                "Purse Rank",
                rank_display,
                help="Ranking among 2026 PGA Tour schedule tournaments"
            )

        with col3:
            # Calculate percentile
            percentile = ((total_tournaments - purse_rank + 1) / total_tournaments * 100)
            if percentile >= 75:
                tier = "🏆 Elite"
                tier_color = "green"
            elif percentile >= 50:
                tier = "⭐ Premium"
                tier_color = "blue"
            elif percentile >= 25:
                tier = "📊 Standard"
                tier_color = "orange"
            else:
                tier = "📉 Lower-Tier"
                tier_color = "red"

            st.metric(
                "Tournament Tier",
                tier,
                help=f"Top {percentile:.0f}% of all tournaments by purse"
            )

        with col4:
            # Show average purse for comparison
            avg_purse = all_purses_df['total_purse'].mean()
            purse_vs_avg = ((tournament_purse - avg_purse) / avg_purse * 100)

            st.metric(
                "vs Avg Purse",
                f"{purse_vs_avg:+.0f}%",
                help=f"Average tour purse: ${avg_purse:,.0f}"
            )

        # Show context about tournament tier
        if percentile >= 75:
            st.success("🏆 **Elite Event** - Top-tier tournament attracting the strongest fields. Consider saving premium OWGR picks for events like this.")
        elif percentile >= 50:
            st.info("⭐ **Premium Event** - Strong purse typically draws quality fields. Good opportunity to use higher-ranked players.")
        elif percentile < 25:
            st.warning("📉 **Lower-Tier Event** - Smaller purse may indicate weaker field. Consider saving top OWGR players for bigger events.")

        st.divider()

    # Get historical data for these players at this tournament
    conn = sqlite3.connect(db.db_path)

    # Build query with field players
    # Include ALL appearances (even missed cuts with position '-')
    placeholders = ','.join(['?'] * len(field_players))
    query = f"""
        SELECT *
        FROM tournament_results
        WHERE tournament_name = ?
        AND player_name IN ({placeholders})
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY year DESC, player_name
    """

    params = [tournament_name] + field_players
    field_history_df = pd.read_sql(query, conn, params=params)
    conn.close()

    if field_history_df.empty:
        st.warning("No historical data available for players in this field")
        st.info("Showing player list only")

        # Show player list
        st.subheader("Players in the Field")
        used_players = db.get_used_players()

        player_list_df = pd.DataFrame({
            'Player': field_players,
            'Status': ['🚫 Used' if p in used_players else '✅ Available' for p in field_players]
        })

        st.dataframe(player_list_df, use_container_width=True, height=600)
        return

    # Get par data for this tournament
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT year, tournament_id
        FROM tournament_results
        WHERE tournament_name = ?
        ORDER BY year DESC
        LIMIT 1
    """, (tournament_name,))
    year_tid = cursor.fetchone()

    tournament_par = 288  # default
    if year_tid:
        par_info = db.get_tournament_par(year_tid[1], year_tid[0])
        if par_info:
            tournament_par = par_info['total_par']
            rounds_played = par_info['rounds']
            par_per_round = par_info['par_per_round']
    else:
        rounds_played = 4
        par_per_round = 72

    conn.close()

    # Convert to numeric and calculate scores
    # Strip "T" prefix from tied positions before converting to numeric
    field_history_df['position_clean'] = field_history_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
    field_history_df['position_numeric'] = pd.to_numeric(field_history_df['position_clean'], errors='coerce')
    field_history_df['total_score_numeric'] = pd.to_numeric(field_history_df['total_score'], errors='coerce')
    field_history_df['earnings_numeric'] = pd.to_numeric(field_history_df['earnings'], errors='coerce')
    field_history_df['score_to_par'] = field_history_df['total_score_numeric'] - tournament_par

    # Mark made cuts
    min_reasonable_score = tournament_par * 0.75
    field_history_df['made_cut'] = (field_history_df['position_numeric'] <= 70) & (field_history_df['total_score_numeric'] >= min_reasonable_score)

    # Calculate stats for players in field
    def calculate_wins(positions):
        return (positions == 1).sum()

    def calculate_top_10s(positions):
        return (positions <= 10).sum()

    def calculate_made_cuts(positions):
        return (positions <= 70).sum()

    def calculate_avg_score_made_cuts(df_subset):
        made_cut_scores = df_subset[df_subset['made_cut']]['score_to_par']
        if len(made_cut_scores) > 0:
            return made_cut_scores.mean()
        return None

    # Aggregate stats
    player_stats = field_history_df.groupby('player_name').agg({
        'year': 'count',  # Count ALL appearances including missed cuts
        'position_numeric': ['mean', 'min', calculate_wins, calculate_top_10s, calculate_made_cuts],
        'earnings_numeric': 'sum'
    }).reset_index()

    avg_scores = field_history_df.groupby('player_name').apply(calculate_avg_score_made_cuts).reset_index()
    avg_scores.columns = ['player_name', 'avg_score_to_par']

    player_stats.columns = ['player_name', 'appearances', 'avg_finish', 'best_finish', 'wins', 'top_10s', 'made_cuts', 'total_earnings']
    player_stats = player_stats.merge(avg_scores, on='player_name', how='left')

    # Add players with no history
    players_with_history = set(player_stats['player_name'].tolist())
    players_without_history = [p for p in field_players if p not in players_with_history]

    if players_without_history:
        no_history_df = pd.DataFrame({
            'player_name': players_without_history,
            'appearances': 0,
            'avg_finish': None,
            'best_finish': None,
            'wins': 0,
            'top_10s': 0,
            'made_cuts': 0,
            'total_earnings': 0,
            'avg_score_to_par': None
        })
        player_stats = pd.concat([player_stats, no_history_df], ignore_index=True)

    # Add OWGR - create both numeric (for sorting) and display versions
    player_stats['owgr_numeric'] = player_stats['player_name'].apply(
        lambda name: db.get_player_owgr(name) if db.get_player_owgr(name) else 9999
    )
    player_stats['owgr'] = player_stats['owgr_numeric'].apply(
        lambda x: str(int(x)) if x < 9999 else 'NR'
    )

    # Calculate field average score to par (for comparison)
    field_avg_score = field_history_df[field_history_df['made_cut']]['score_to_par'].mean()
    if pd.isna(field_avg_score):
        field_avg_score = 0

    # Get recent form data for all players
    conn_recent = sqlite3.connect(db.db_path)
    max_year = field_history_df['year'].max() if not field_history_df.empty else 2025
    min_year_all = max_year - 2  # Last 2-3 years for overall form calculation

    recent_form_data = {}
    for player in player_stats['player_name']:
        # Get ALL recent events (last 2-3 years for value calculation)
        recent_df = pd.read_sql("""
            SELECT position, year, tournament_id
            FROM tournament_results
            WHERE player_name = ?
            AND year >= ?
            AND position IS NOT NULL
            AND position != 'None'
            ORDER BY year DESC, tournament_id DESC
        """, conn_recent, params=(player, min_year_all))

        # Get last 10 tournaments from a LONGER timeframe to ensure we have 10 events
        # Some players don't play many events, so look back further
        last_10_query_df = pd.read_sql("""
            SELECT position, year, tournament_id
            FROM tournament_results
            WHERE player_name = ?
            AND position IS NOT NULL
            AND position != 'None'
            ORDER BY year DESC, tournament_id DESC
            LIMIT 10
        """, conn_recent, params=(player,))

        last_10_df = last_10_query_df  # Already limited to 10 by SQL

        if not recent_df.empty:
            recent_df['position_clean'] = recent_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
            recent_df['position_numeric'] = pd.to_numeric(recent_df['position_clean'], errors='coerce')
            recent_df['made_cut'] = recent_df['position_numeric'] <= 70

            recent_form_data[player] = {
                'recent_events': len(recent_df),
                'recent_cut_rate': (recent_df['made_cut'].sum() / len(recent_df) * 100) if len(recent_df) > 0 else 0,
                'recent_avg_finish': recent_df[recent_df['made_cut']]['position_numeric'].mean() if recent_df['made_cut'].any() else 999,
                'recent_top10s': (recent_df['position_numeric'] <= 10).sum(),
                'recent_made_cuts': recent_df['made_cut'].sum()
            }
        else:
            recent_form_data[player] = {
                'recent_events': 0,
                'recent_cut_rate': 0,
                'recent_avg_finish': 999,
                'recent_top10s': 0,
                'recent_made_cuts': 0
            }

        # Calculate Last 10 specific metrics
        if not last_10_df.empty:
            last_10_df['position_clean'] = last_10_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
            last_10_df['position_numeric'] = pd.to_numeric(last_10_df['position_clean'], errors='coerce')
            last_10_df['made_cut'] = last_10_df['position_numeric'] <= 70

            # Average finish in last 10 (including missed cuts as high number)
            avg_finish_last_10 = last_10_df['position_numeric'].mean() if len(last_10_df) > 0 else None

            # Cut percentage in last 10
            cut_pct_last_10 = (last_10_df['made_cut'].sum() / len(last_10_df) * 100) if len(last_10_df) > 0 else 0

            recent_form_data[player]['last_10_avg'] = avg_finish_last_10
            recent_form_data[player]['last_10_cut_pct'] = cut_pct_last_10
            recent_form_data[player]['last_10_count'] = len(last_10_df)
        else:
            recent_form_data[player]['last_10_avg'] = None
            recent_form_data[player]['last_10_cut_pct'] = 0
            recent_form_data[player]['last_10_count'] = 0

    conn_recent.close()

    # Calculate comprehensive value metric using unified ValueCalculator
    value_calc = ValueCalculator()

    def calculate_value_score(row):
        """
        Uses unified ValueCalculator with regression-optimized weights
        Maps field view data structure to ValueCalculator expected format
        """
        # Map field view columns to ValueCalculator expected names
        player_name = row['player_name']
        recent_data = recent_form_data.get(player_name, {
            'recent_events': 0,
            'recent_cut_rate': 0,
            'recent_avg_finish': 999,
            'recent_top10s': 0,
            'recent_made_cuts': 0
        })

        player_data = pd.Series({
            'events': row['appearances'],
            'wins': row['wins'],
            'top_10s': row['top_10s'],
            'avg_finish': row['avg_finish'] if pd.notna(row['avg_finish']) and row['avg_finish'] < 999 else None,
            'best_finish': row['best_finish'] if pd.notna(row['best_finish']) and row['best_finish'] < 999 else 999,
            'made_cuts': row['made_cuts'],
            'recent_avg_finish': recent_data.get('recent_avg_finish', 999),
            'recent_events': recent_data.get('recent_events', 0),
            'recent_cut_rate': recent_data.get('recent_cut_rate', 0) / 100,
            'recent_top10s': recent_data.get('recent_top10s', 0),
            'recent_made_cuts': recent_data.get('recent_made_cuts', 0),
            'owgr_numeric': row['owgr_numeric']
        })

        result = value_calc.calculate_value(player_data)
        return round(result['final_value_score'], 1)

    player_stats['value_numeric'] = player_stats.apply(calculate_value_score, axis=1)
    player_stats['value'] = player_stats['value_numeric'].apply(
        lambda x: str(x) if x > 0 else '0'
    )

    # Check used players
    used_players = db.get_used_players()
    player_stats['status'] = player_stats['player_name'].apply(
        lambda x: '🚫 Used' if x in used_players else '✅ Available'
    )

    # Add Last 10 tournament metrics for quick form assessment
    player_stats['last_10_avg'] = player_stats['player_name'].apply(
        lambda x: recent_form_data.get(x, {}).get('last_10_avg')
    )
    player_stats['last_10_cut_pct'] = player_stats['player_name'].apply(
        lambda x: recent_form_data.get(x, {}).get('last_10_cut_pct', 0)
    )
    player_stats['last_10_count'] = player_stats['player_name'].apply(
        lambda x: recent_form_data.get(x, {}).get('last_10_count', 0)
    )

    # Sort by value score (highest first)
    player_stats = player_stats.sort_values('value_numeric', ascending=False)

    # Get year range for historical data
    years_in_data = sorted(field_history_df['year'].unique())
    if len(years_in_data) > 0:
        first_year = years_in_data[0]
        last_year = years_in_data[-1]
        year_count = len(years_in_data)
        years_display = f"Historical Data: {first_year}-{last_year} ({year_count} years)"
    else:
        years_display = "No historical data"

    # Display stats
    st.subheader(f"Field Performance at {tournament_name}")
    st.caption(f"Showing {len(player_stats)} players | {years_display} | Course Par: {tournament_par} ({rounds_played} rounds × {par_per_round})")

    # Value metric explanation
    with st.expander("ℹ️ About the Value Score", expanded=False):
        st.markdown("""
        **Value Score (0-100)** is a comprehensive metric combining multiple factors:

        - **Tournament History (40%)**: Cut rate, avg finish, best finish, top 10 rate at THIS tournament
        - **Recent Form (30%)**: Performance across all tournaments in last 3 years
        - **Score Quality (15%)**: How their scores compare to field average
        - **OWGR (15%)**: World ranking as baseline talent indicator

        **Score Ranges:**
        - 🏆 **90-100**: Elite pick - Top performer with strong form
        - ⭐ **75-89**: Premium pick - Consistent, good value
        - ✅ **60-74**: Solid pick - Decent history and form
        - ⚠️ **40-59**: Risky pick - Limited/inconsistent
        - ❌ **0-39**: Avoid - Poor track record
        """)

    # Show filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        show_only_available = st.checkbox("Show only available players", value=False)

    with col2:
        show_only_with_history = st.checkbox("Show only players with history", value=False)

    with col3:
        # Min appearances slider
        max_appearances = int(player_stats['appearances'].max())
        if max_appearances > 1:
            min_appearances = st.slider(
                "Minimum Appearances",
                min_value=0,
                max_value=max_appearances,
                value=0,
                help="Filter to show only players with at least this many appearances"
            )
        else:
            min_appearances = 0
            st.caption("All players have ≤1 appearance")

    # Apply filters
    display_stats = player_stats.copy()

    if show_only_available:
        display_stats = display_stats[display_stats['status'] == '✅ Available']

    if show_only_with_history:
        display_stats = display_stats[display_stats['appearances'] > 0]

    if min_appearances > 0:
        display_stats = display_stats[display_stats['appearances'] >= min_appearances]

    # Format display
    display_df = display_stats.copy()
    # Replace None in avg_finish with 999 so it sorts to bottom
    display_df['avg_finish'] = display_df['avg_finish'].fillna(999).round(1)
    # Replace None in best_finish with 999 so it sorts to bottom
    display_df['best_finish'] = display_df['best_finish'].fillna(999).astype('Int64')
    display_df['total_earnings'] = display_df['total_earnings'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
    )
    display_df['avg_score_sortable'] = display_df['avg_score_to_par'].round(0)
    display_df['made_cut_pct'] = (display_df['made_cuts'] / display_df['appearances'] * 100).round(0).astype('Int64')
    display_df['made_cut_pct'] = display_df['made_cut_pct'].apply(lambda x: x if pd.notna(x) else 0)

    # Format Last 10 metrics
    display_df['last_10_avg_display'] = display_df['last_10_avg'].apply(
        lambda x: round(x, 1) if pd.notna(x) and x < 999 else None
    )
    display_df['last_10_cut_pct_display'] = display_df['last_10_cut_pct'].apply(
        lambda x: int(x) if pd.notna(x) and x > 0 else None
    )

    # Reset index so we can properly access rows by position
    display_df = display_df.reset_index(drop=True)

    # Display table with row selection
    st.caption("💡 Click on any player row to view detailed analysis below")

    st.dataframe(
        display_df[['player_name', 'appearances', 'avg_finish', 'best_finish', 'top_10s', 'made_cuts', 'made_cut_pct', 'last_10_avg_display', 'last_10_cut_pct_display', 'avg_score_sortable', 'owgr_numeric', 'value_numeric', 'status']],
        column_config={
            "player_name": st.column_config.TextColumn("Player", width="medium"),
            "appearances": st.column_config.NumberColumn("Apps", format="%d", help="Times played this tournament"),
            "avg_finish": st.column_config.NumberColumn("Avg", format="%.1f", help="Average finish position"),
            "best_finish": st.column_config.NumberColumn("Best", format="%d", help="Best finish"),
            "top_10s": st.column_config.NumberColumn("Top 10s", format="%d"),
            "made_cuts": st.column_config.NumberColumn("Cuts", format="%d"),
            "made_cut_pct": st.column_config.NumberColumn("Cut %", format="%d%%", help="Cut percentage at this tournament"),
            "last_10_avg_display": st.column_config.NumberColumn("L10 Avg", format="%.1f", help="Average finish position in last 10 tournaments (all events)"),
            "last_10_cut_pct_display": st.column_config.NumberColumn("L10 Cut%", format="%d%%", help="Percentage of cuts made in last 10 tournaments"),
            "avg_score_sortable": st.column_config.NumberColumn("Avg Score", format="%d", help="Avg score to par (made cuts only)"),
            "owgr_numeric": st.column_config.NumberColumn("OWGR", format="%d", help="World ranking (9999 = Not Ranked)"),
            "value_numeric": st.column_config.NumberColumn("Value", format="%.1f", help="""COMPREHENSIVE VALUE SCORE (0-100)

CALCULATION BREAKDOWN:

1️⃣ TOURNAMENT HISTORY (40% weight)
   • Cut Rate (25%): (Made Cuts ÷ Appearances) × 100
   • Avg Finish (35%): max(0, 100 - (Avg Position - 1) × 1.4)
     → 1st place = 100 pts, 10th = 87 pts, 20th = 73 pts
   • Best Finish (20%): max(0, 100 - (Best Position - 1) × 1.4)
   • Top 10 Rate (20%): (Top 10s ÷ Appearances) × 100 × 1.5 (capped at 100)

2️⃣ RECENT FORM (30% weight)
   • Cut Rate Last 3 Years (30%): % of cuts made across all tournaments
   • Avg Finish Last 3 Years (70%): Normalized position when made cut

3️⃣ SCORE QUALITY (15% weight)
   • 50 + (Field Avg Score to Par - Player Avg Score to Par) × 10
   • Better than field avg = bonus points, worse = penalty

4️⃣ OWGR RANKING (15% weight)
   • max(0, 100 - (OWGR ÷ 2))
   • Top 10 world = 95+ pts, Top 50 = 75+ pts, Top 100 = 50+ pts

FINAL = (1×40% + 2×30% + 3×15% + 4×15%)

RANGES:
🏆 90-100: Elite pick (top performer + strong form)
⭐ 75-89: Premium pick (consistent, good value)
✅ 60-74: Solid pick (decent history/form)
⚠️ 40-59: Risky pick (limited/inconsistent)
❌ 0-39: Avoid (poor track record)"""),
            "status": st.column_config.TextColumn("Status", width="small")
        },
        hide_index=True,
        use_container_width=True,
        height=600,
        on_select="rerun",
        selection_mode="single-row",
        key="field_table_selection"
    )

    # Get selected player from table (stored in session state)
    selected_from_table = None

    if "field_table_selection" in st.session_state:
        selection_state = st.session_state.field_table_selection

        try:
            # Method 1: Direct access to selection attribute
            if hasattr(selection_state, 'selection') and hasattr(selection_state.selection, 'rows'):
                if len(selection_state.selection.rows) > 0:
                    selected_row_idx = selection_state.selection.rows[0]
                    if selected_row_idx < len(display_df):
                        selected_from_table = display_df.iloc[selected_row_idx]['player_name']
            # Method 2: Dictionary access
            elif isinstance(selection_state, dict) and 'rows' in selection_state:
                if len(selection_state['rows']) > 0:
                    selected_row_idx = selection_state['rows'][0]
                    if selected_row_idx < len(display_df):
                        selected_from_table = display_df.iloc[selected_row_idx]['player_name']
        except Exception:
            pass  # Silently handle any selection access errors

    # Quick Player Analysis
    st.divider()
    st.subheader("🔍 Quick Player Analysis")

    # Use table selection if available, otherwise use dropdown
    player_list = sorted(display_stats['player_name'].tolist())

    if selected_from_table:
        # Auto-select from table click
        selected_analysis_player = selected_from_table
        st.info(f"Selected from table: **{selected_analysis_player}** (Use dropdown to select a different player)")

        # Also show dropdown for manual selection
        manual_selection = st.selectbox(
            "Or select a different player:",
            options=[""] + player_list,
            key="field_player_analysis"
        )

        # Manual selection overrides table selection
        if manual_selection:
            selected_analysis_player = manual_selection
    else:
        # No table selection, just use dropdown
        selected_analysis_player = st.selectbox(
            "Click a player row above or select from dropdown:",
            options=[""] + player_list,
            key="field_player_analysis"
        )

    if selected_analysis_player:
        render_player_quick_analysis(selected_analysis_player, tournament_name, db, field_history_df, tournament_par)

    # Insights
    st.divider()
    st.subheader("💡 Field Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        available_count = len(display_stats[display_stats['status'] == '✅ Available'])
        st.metric("Available Players", available_count)

    with col2:
        with_history_count = len(display_stats[display_stats['appearances'] > 0])
        st.metric("Players with History", with_history_count)

    with col3:
        no_history_count = len(display_stats[display_stats['appearances'] == 0])
        st.metric("First-Time Players", no_history_count)

    # Top recommendations
    if len(display_stats[display_stats['status'] == '✅ Available']) > 0:
        st.divider()
        st.subheader("🎯 Top Available Players")

        available_stats = display_stats[display_stats['status'] == '✅ Available']
        available_with_history = available_stats[available_stats['appearances'] > 0]

        if len(available_with_history) > 0:
            top_by_avg = available_with_history.nsmallest(5, 'avg_finish')

            for i, row in enumerate(top_by_avg.iterrows(), 1):
                _, player = row
                st.markdown(f"**{i}. {player['player_name']}** - Avg Finish: {player['avg_finish']:.1f}, Best: {int(player['best_finish']) if pd.notna(player['best_finish']) else 'N/A'}, Apps: {int(player['appearances'])}")


def render_player_quick_analysis(player_name, tournament_name, db, field_history_df, tournament_par):
    """Render quick analysis tabs for a selected player"""
    import plotly.graph_objects as go
    from datetime import datetime

    # Check if player is used
    used_players = db.get_used_players()
    is_used = player_name in used_players

    # Status badge
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### {player_name}")
    with col2:
        if is_used:
            st.error("🚫 Used")
        else:
            st.success("✅ Available")

    # Create tabs for different analysis views
    tab1, tab2 = st.tabs(["📊 Tournament History", "🔥 Recent Form"])

    with tab1:
        # Player's performance at THIS tournament (Player Deep Dive equivalent)
        st.markdown(f"**Performance at {tournament_name}**")

        # Filter for this player
        player_tournament_history = field_history_df[field_history_df['player_name'] == player_name].copy()

        if player_tournament_history.empty:
            st.info(f"{player_name} has no history at this tournament")
        else:
            # Summary stats
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                appearances = len(player_tournament_history)
                st.metric("Appearances", appearances)

            with col2:
                made_cuts = player_tournament_history['made_cut'].sum()
                st.metric("Made Cuts", made_cuts)

            with col3:
                avg_finish = player_tournament_history[player_tournament_history['made_cut']]['position_numeric'].mean()
                st.metric("Avg Finish", f"{avg_finish:.1f}" if not pd.isna(avg_finish) else "N/A")

            with col4:
                best_finish = player_tournament_history['position_numeric'].min()
                st.metric("Best Finish", f"{int(best_finish)}" if not pd.isna(best_finish) else "N/A")

            # Year by year table
            st.markdown("**Year-by-Year Results**")
            display_history = player_tournament_history.sort_values('year', ascending=False).copy()

            # Format earnings
            display_history['earnings_display'] = display_history['earnings_numeric'].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
            )

            # Format score to par
            display_history['score_to_par_display'] = display_history.apply(
                lambda row: f"{int(row['score_to_par']):+d}" if row['made_cut'] and pd.notna(row['score_to_par']) else "",
                axis=1
            )

            st.dataframe(
                display_history[['year', 'position', 'score_to_par_display', 'total_score', 'earnings_display', 'made_cut']],
                column_config={
                    "year": st.column_config.NumberColumn("Year", format="%d"),
                    "position": "Finish",
                    "score_to_par_display": "To Par",
                    "total_score": st.column_config.NumberColumn("Score", format="%d"),
                    "earnings_display": "Earnings",
                    "made_cut": st.column_config.CheckboxColumn("Made Cut")
                },
                hide_index=True,
                use_container_width=True
            )

            # Chart
            if len(player_tournament_history) >= 2:
                fig = go.Figure()
                made_cut_data = player_tournament_history[player_tournament_history['made_cut']]

                if not made_cut_data.empty:
                    fig.add_trace(go.Scatter(
                        x=made_cut_data['year'],
                        y=made_cut_data['position_numeric'],
                        mode='lines+markers',
                        name='Finish Position',
                        line=dict(color='#1f77b4', width=2),
                        marker=dict(size=8)
                    ))

                    fig.update_layout(
                        title=f"{player_name}'s Performance Trend",
                        xaxis_title="Year",
                        yaxis_title="Finish Position",
                        yaxis=dict(autorange='reversed'),
                        height=300
                    )

                    st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Player's recent form across ALL tournaments (Recent Form equivalent)
        st.markdown("**Recent Form Across All Tournaments (Last 3 Years)**")

        # Get all recent tournament results for this player (last 3 years)
        conn = sqlite3.connect(db.db_path)

        # Get the most recent year available for this player
        max_year_df = pd.read_sql("""
            SELECT MAX(year) as max_year
            FROM tournament_results
            WHERE player_name = ?
        """, conn, params=(player_name,))

        if max_year_df.empty or pd.isna(max_year_df['max_year'].iloc[0]):
            st.info(f"No tournament data found for {player_name}")
            conn.close()
        else:
            max_year = int(max_year_df['max_year'].iloc[0])
            min_year = max_year - 2  # Last 3 years

            recent_form_df = pd.read_sql("""
                SELECT
                    tr.year,
                    tr.tournament_name,
                    tr.position,
                    tr.total_score,
                    tr.earnings,
                    tr.tournament_id,
                    COALESCE(
                        t.start_date,
                        t.end_date,
                        t2026.date
                    ) as tournament_date
                FROM tournament_results tr
                LEFT JOIN tournaments t
                    ON (tr.tournament_id || '_' || tr.year) = t.tournament_id
                LEFT JOIN tournament_2026_ids t2026
                    ON tr.tournament_name = t2026.tournament_name
                    AND tr.year = 2026
                WHERE tr.player_name = ?
                AND tr.year >= ?
                AND tr.position IS NOT NULL
                AND tr.position <> 'None'
            """, conn, params=(player_name, min_year))
            conn.close()

            if recent_form_df.empty:
                st.info(f"No recent tournament data found for {player_name} (years {min_year}-{max_year})")
            else:
                # Clean position data
                recent_form_df['position_clean'] = recent_form_df['position'].astype(str).str.replace('T', '').str.replace('T-', '')
                recent_form_df['position_numeric'] = pd.to_numeric(recent_form_df['position_clean'], errors='coerce')
                recent_form_df['made_cut'] = recent_form_df['position_numeric'] <= 70

                # Create sortable date column first (for sorting)
                recent_form_df['sort_date'] = pd.to_datetime(recent_form_df['tournament_date'], errors='coerce')

                # For rows without dates, use year + 6 months (mid-year) as estimate for sorting only
                recent_form_df['sort_date_filled'] = recent_form_df['sort_date'].fillna(
                    pd.to_datetime(recent_form_df['year'].astype(str) + '-06-01')
                )

                # Sort by date descending (most recent first)
                recent_form_df = recent_form_df.sort_values('sort_date_filled', ascending=False)

                # Format date for display AFTER sorting
                # Only show actual dates from database, not estimated dates
                recent_form_df['date_display'] = recent_form_df['sort_date'].dt.strftime('%b %d, %Y')
                # If no actual date available, show year only (this should be very rare now)
                recent_form_df['date_display'] = recent_form_df['date_display'].fillna(recent_form_df['year'].astype(str))

                # Summary stats
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    recent_events = len(recent_form_df)
                    st.metric("Events (3 yrs)", recent_events)

                with col2:
                    recent_cuts = recent_form_df['made_cut'].sum()
                    cut_pct = (recent_cuts / recent_events * 100) if recent_events > 0 else 0
                    st.metric("Made Cuts", f"{recent_cuts} ({cut_pct:.0f}%)")

                with col3:
                    recent_avg = recent_form_df[recent_form_df['made_cut']]['position_numeric'].mean()
                    st.metric("Avg Finish", f"{recent_avg:.1f}" if not pd.isna(recent_avg) else "N/A")

                with col4:
                    recent_best = recent_form_df['position_numeric'].min()
                    st.metric("Best Finish", f"{int(recent_best)}" if not pd.isna(recent_best) else "N/A")

                # Recent results table
                st.markdown(f"**Tournaments: {min_year}-{max_year} ({len(recent_form_df)} events)**")

                # Format earnings
                recent_form_df['earnings_display'] = recent_form_df['earnings'].apply(
                    lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
                )

                st.dataframe(
                    recent_form_df[['date_display', 'tournament_name', 'position', 'total_score', 'earnings_display', 'made_cut']],
                    column_config={
                        "date_display": st.column_config.TextColumn("Date", width="small"),
                        "tournament_name": "Tournament",
                        "position": "Finish",
                        "total_score": st.column_config.NumberColumn("Score", format="%d"),
                        "earnings_display": "Earnings",
                        "made_cut": st.column_config.CheckboxColumn("Made Cut")
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=400
                )

    # Quick action button
    st.divider()
    if not is_used:
        if st.button(f"✅ Mark {player_name} as Used", key=f"mark_used_{player_name}", use_container_width=True, type="primary"):
            db.mark_player_used(player_name, tournament_name, f"Week {datetime.now().isocalendar()[1]}")
            st.success(f"Marked {player_name} as used!")
            st.rerun()
    else:
        if st.button(f"↩️ Remove {player_name} from Used List", key=f"remove_used_{player_name}", use_container_width=True):
            db.remove_used_player(player_name)
            st.success(f"Removed {player_name} from used list!")
            st.rerun()
