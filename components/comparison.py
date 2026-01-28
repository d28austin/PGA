"""
Player Comparison Component
Side-by-side comparison of multiple players
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_comparison_view(tournament_name, db):
    """Render the player comparison view"""

    st.subheader(f"⚖️ Compare Players for {tournament_name}")

    # Get all players who have played this tournament (by name)
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    # Include ALL players (even those who missed cuts)
    all_players = pd.read_sql("""
        SELECT DISTINCT player_name
        FROM tournament_results
        WHERE tournament_name = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY player_name
    """, conn, params=(tournament_name,))
    conn.close()

    if all_players.empty:
        st.info("No player data available for this tournament.")
        return

    # Player selection
    st.markdown("Select 2-4 players to compare:")

    col1, col2, col3, col4 = st.columns(4)

    player_list = sorted(all_players['player_name'].unique())
    used_players = db.get_used_players()

    with col1:
        player1 = st.selectbox("Player 1", options=[""] + player_list, key="comp_p1")

    with col2:
        player2 = st.selectbox("Player 2", options=[""] + player_list, key="comp_p2")

    with col3:
        player3 = st.selectbox("Player 3 (optional)", options=[""] + player_list, key="comp_p3")

    with col4:
        player4 = st.selectbox("Player 4 (optional)", options=[""] + player_list, key="comp_p4")

    # Collect selected players
    selected_players = [p for p in [player1, player2, player3, player4] if p]

    if len(selected_players) < 2:
        st.warning("Please select at least 2 players to compare")
        return

    st.divider()

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

    min_reasonable_score = tournament_par * 0.75
    conn.close()

    # Fetch data for all selected players
    player_data = {}
    for player in selected_players:
        # Get player history by tournament name
        # Include ALL appearances (even missed cuts with position '-')
        conn = sqlite3.connect(db.db_path)
        history = pd.read_sql("""
            SELECT *
            FROM tournament_results
            WHERE player_name = ?
            AND tournament_name = ?
            AND position IS NOT NULL
            AND position != 'None'
            ORDER BY year DESC
        """, conn, params=(player, tournament_name))
        conn.close()

        if not history.empty:
            # Strip "T" prefix from tied positions before converting to numeric
            history['position_clean'] = history['position'].astype(str).str.replace('T', '').str.replace('T-', '')
            history['position_numeric'] = pd.to_numeric(history['position_clean'], errors='coerce')
            history['total_score_numeric'] = pd.to_numeric(history['total_score'], errors='coerce')
            history['score_to_par'] = history['total_score_numeric'] - tournament_par
            history['made_cut'] = (history['position_numeric'] <= 70) & (history['total_score_numeric'] >= min_reasonable_score)
            player_data[player] = history

    if not player_data:
        st.warning("No historical data found for selected players")
        return

    # Summary comparison table
    st.subheader("📊 Head-to-Head Statistics")

    comparison_stats = []
    for player, history in player_data.items():
        # Calculate avg score only for made cuts
        made_cut_scores = history[history['made_cut']]['score_to_par']
        avg_score = made_cut_scores.mean() if len(made_cut_scores) > 0 else None

        stats = {
            'Player': player,
            'Appearances': len(history),
            'Avg Finish': history['position_numeric'].mean(),
            'Best Finish': history['position_numeric'].min(),
            'Total Earnings': history['earnings'].sum(),
            'Avg Score': avg_score,
            'Status': '🚫 Used' if player in used_players else '✅ Available'
        }
        comparison_stats.append(stats)

    comparison_df = pd.DataFrame(comparison_stats)

    # Format the dataframe for display
    display_df = comparison_df.copy()
    display_df['Avg Finish'] = display_df['Avg Finish'].round(1)
    display_df['Best Finish'] = display_df['Best Finish'].astype('Int64')
    display_df['Total Earnings'] = display_df['Total Earnings'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else "N/A"
    )
    # Round Avg Score for display
    display_df['Avg Score Numeric'] = display_df['Avg Score'].round(0)

    st.dataframe(
        display_df,
        column_config={
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Appearances": st.column_config.NumberColumn("Apps", format="%d"),
            "Avg Finish": st.column_config.NumberColumn("Avg Finish", format="%.1f"),
            "Best Finish": st.column_config.NumberColumn("Best", format="%d"),
            "Total Earnings": "Total $$",
            "Avg Score Numeric": st.column_config.NumberColumn("Avg Score", format="%d", help="Average score relative to par (made cuts only)"),
            "Status": "Status"
        },
        hide_index=True,
        use_container_width=True,
        column_order=["Player", "Appearances", "Avg Finish", "Best Finish", "Total Earnings", "Avg Score Numeric", "Status"]
    )

    # Highlight best performer
    best_avg_player = comparison_df.loc[comparison_df['Avg Finish'].idxmin(), 'Player']

    # Only show earnings comparison if there's valid earnings data
    has_earnings = comparison_df['Total Earnings'].notna().any() and (comparison_df['Total Earnings'] > 0).any()

    if has_earnings:
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🏆 Best Avg Finish: **{best_avg_player}**")
        with col2:
            best_earnings_player = comparison_df.loc[comparison_df['Total Earnings'].idxmax(), 'Player']
            st.success(f"💰 Most Earnings: **{best_earnings_player}**")
    else:
        st.success(f"🏆 Best Avg Finish: **{best_avg_player}**")
        st.info("💰 Earnings data not available from ESPN API")

    # Visualizations
    st.divider()
    st.subheader("📈 Performance Comparison Charts")

    tab1, tab2, tab3 = st.tabs(["Finish Position Trends", "Earnings Comparison", "Consistency Analysis"])

    with tab1:
        # Line chart comparing finish positions over time
        fig = go.Figure()

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for idx, (player, history) in enumerate(player_data.items()):
            fig.add_trace(go.Scatter(
                x=history['year'],
                y=history['position_numeric'],
                mode='lines+markers',
                name=player,
                line=dict(color=colors[idx % len(colors)], width=2),
                marker=dict(size=8)
            ))

        fig.update_layout(
            title="Finish Position Comparison Over Time",
            xaxis_title="Year",
            yaxis_title="Finish Position",
            yaxis=dict(autorange='reversed'),
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Bar chart comparing total earnings by year
        fig2 = go.Figure()

        for idx, (player, history) in enumerate(player_data.items()):
            fig2.add_trace(go.Bar(
                x=history['year'],
                y=history['earnings'],
                name=player,
                marker_color=colors[idx % len(colors)]
            ))

        fig2.update_layout(
            title="Earnings Comparison by Year",
            xaxis_title="Year",
            yaxis_title="Earnings ($)",
            barmode='group',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        # Box plot showing consistency
        fig3 = go.Figure()

        for player, history in player_data.items():
            fig3.add_trace(go.Box(
                y=history['position_numeric'],
                name=player,
                boxmean='sd'
            ))

        fig3.update_layout(
            title="Finish Position Distribution (Consistency)",
            yaxis_title="Finish Position",
            yaxis=dict(autorange='reversed'),
            showlegend=True
        )

        st.plotly_chart(fig3, use_container_width=True)

        st.caption("💡 Tighter box = more consistent performance")

    # Recent form comparison
    st.divider()
    st.subheader("🔥 Recent Form (Last 3 Years)")

    recent_form = []
    for player, history in player_data.items():
        recent = history.nlargest(3, 'year')
        if not recent.empty:
            recent_form.append({
                'Player': player,
                'Recent Avg Finish': recent['position_numeric'].mean(),
                'Recent Best': recent['position_numeric'].min(),
                'Recent Earnings': recent['earnings'].sum(),
                'Status': '🚫 Used' if player in used_players else '✅ Available'
            })

    if recent_form:
        recent_df = pd.DataFrame(recent_form).sort_values('Recent Avg Finish')

        display_recent = recent_df.copy()
        display_recent['Recent Avg Finish'] = display_recent['Recent Avg Finish'].round(1)
        display_recent['Recent Best'] = display_recent['Recent Best'].astype('Int64')
        display_recent['Recent Earnings'] = display_recent['Recent Earnings'].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else "N/A"
        )

        st.dataframe(
            display_recent,
            column_config={
                "Player": "Player",
                "Recent Avg Finish": st.column_config.NumberColumn("Recent Avg", format="%.1f"),
                "Recent Best": st.column_config.NumberColumn("Best Finish", format="%d"),
                "Recent Earnings": "Recent $$",
                "Status": "Status"
            },
            hide_index=True,
            use_container_width=True
        )

        # Recommendation
        best_recent = recent_df.iloc[0]['Player']
        if best_recent not in used_players:
            st.success(f"🎯 **Recommendation:** Based on recent form, consider **{best_recent}**")
        else:
            available_players = recent_df[recent_df['Status'] == '✅ Available']
            if not available_players.empty:
                best_available = available_players.iloc[0]['Player']
                st.info(f"🎯 **Recommendation:** Best available player based on recent form: **{best_available}**")

    # Download comparison
    st.divider()
    if st.button("📥 Export Comparison to CSV"):
        comparison_df.to_csv('player_comparison.csv', index=False)
        st.success("Exported to player_comparison.csv")
