"""
Player Deep Dive Component
Detailed analysis of individual player performance
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


def render_player_view(tournament_name, db, fetcher):
    """Render the player deep dive analysis view"""

    st.subheader(f"👤 Player Analysis for {tournament_name}")

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

    # Player selector
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_player = st.selectbox(
            "Select a player to analyze:",
            options=sorted(all_players['player_name'].unique()),
            help="Choose a player to see their complete tournament history"
        )

    with col2:
        # Check if player is already used
        used_players = db.get_used_players()
        if selected_player in used_players:
            st.error("🚫 Used")
        else:
            st.success("✅ Available")

    if not selected_player:
        return

    st.divider()

    # Get player's tournament history (by tournament name)
    # Include ALL appearances (even missed cuts with position '-')
    conn = sqlite3.connect(db.db_path)
    player_history = pd.read_sql("""
        SELECT *
        FROM tournament_results
        WHERE player_name = ?
        AND tournament_name = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY year DESC
    """, conn, params=(selected_player, tournament_name))
    conn.close()

    if player_history.empty:
        st.warning(f"No historical data found for {selected_player} at this tournament")
        return

    # Get par data for each year/tournament_id
    conn = sqlite3.connect(db.db_path)
    year_tournament_pairs = player_history[['year', 'tournament_id']].values.tolist()

    # Get par info for each tournament/year
    par_data = {}
    for year, tid in year_tournament_pairs:
        par_info = db.get_tournament_par(tid, year)
        if par_info:
            par_data[year] = par_info['total_par']

    # Use most recent par if available, otherwise default
    tournament_par = list(par_data.values())[0] if par_data else 288
    conn.close()

    # Convert to numeric and calculate scores relative to par
    # Strip "T" prefix from tied positions before converting to numeric
    player_history['position_clean'] = player_history['position'].astype(str).str.replace('T', '').str.replace('T-', '')
    player_history['position_numeric'] = pd.to_numeric(player_history['position_clean'], errors='coerce')
    player_history['total_score_numeric'] = pd.to_numeric(player_history['total_score'], errors='coerce')

    # Calculate score to par for each year
    player_history['score_to_par'] = player_history.apply(
        lambda row: row['total_score_numeric'] - par_data.get(row['year'], tournament_par) if pd.notna(row['total_score_numeric']) else None,
        axis=1
    )

    # Mark made cuts (position <= 70 and reasonable score)
    min_reasonable_score = tournament_par * 0.75
    player_history['made_cut'] = (player_history['position_numeric'] <= 70) & (player_history['total_score_numeric'] >= min_reasonable_score)

    # Summary metrics
    st.subheader(f"📈 {selected_player} - Career Stats at {tournament_name}")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        appearances = len(player_history)
        st.metric("Appearances", appearances)

    with col2:
        avg_finish = player_history['position_numeric'].mean()
        st.metric("Avg Finish", f"{avg_finish:.1f}" if not pd.isna(avg_finish) else "N/A")

    with col3:
        best_finish = player_history['position_numeric'].min()
        st.metric("Best Finish", f"{int(best_finish)}" if not pd.isna(best_finish) else "N/A")

    with col4:
        # Average score (only made cuts)
        made_cut_scores = player_history[player_history['made_cut']]['score_to_par']
        if len(made_cut_scores) > 0:
            avg_score_to_par = made_cut_scores.mean()
            if avg_score_to_par == 0:
                score_display = "E"
            elif avg_score_to_par > 0:
                score_display = f"+{int(round(avg_score_to_par))}"
            else:
                score_display = f"{int(round(avg_score_to_par))}"
        else:
            score_display = "N/A"
        st.metric("Avg Score", score_display, help="Average score relative to par (made cuts only)")

    with col5:
        total_earnings = player_history['earnings'].sum()
        earnings_display = f"${total_earnings:,.0f}" if pd.notna(total_earnings) and total_earnings > 0 else "N/A"
        st.metric("Total Earnings", earnings_display)

    # Performance table
    st.divider()
    st.subheader("Year-by-Year Performance")

    display_history = player_history.sort_values('year', ascending=False).copy()
    display_history['earnings_formatted'] = display_history['earnings'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else "N/A"
    )

    # Format score to par column - only show for made cuts
    display_history['score_to_par_display'] = display_history.apply(
        lambda row: round(row['score_to_par']) if row['made_cut'] and pd.notna(row['score_to_par']) else None,
        axis=1
    )

    st.dataframe(
        display_history[['year', 'position', 'score_to_par_display', 'total_score', 'earnings_formatted', 'made_cut']],
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "position": "Finish",
            "score_to_par_display": st.column_config.NumberColumn("To Par", format="%d", help="Score relative to par (made cuts only). Negative is under par (better)."),
            "total_score": st.column_config.NumberColumn("Total Score", format="%d", help="Total strokes. Low numbers for missed cuts are only 2 rounds."),
            "earnings_formatted": "Earnings",
            "made_cut": st.column_config.CheckboxColumn("Made Cut", help="Player finished all 4 rounds")
        },
        hide_index=True,
        use_container_width=True
    )

    # Visualizations
    st.divider()
    st.subheader("Performance Trends")

    tab1, tab2, tab3 = st.tabs(["Finish Position Trend", "Earnings Over Time", "Score Analysis"])

    with tab1:
        # Line chart of finish positions
        fig1 = go.Figure()

        fig1.add_trace(go.Scatter(
            x=player_history['year'],
            y=player_history['position_numeric'],
            mode='lines+markers',
            name='Finish Position',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=10)
        ))

        fig1.update_layout(
            title=f"{selected_player}'s Finish Position History",
            xaxis_title="Year",
            yaxis_title="Finish Position",
            yaxis=dict(autorange='reversed'),  # Lower is better
            hovermode='x unified'
        )

        st.plotly_chart(fig1, use_container_width=True)

        # Trend analysis
        if len(player_history) >= 3:
            recent_avg = player_history.nsmallest(3, 'year')['position_numeric'].mean()
            older_avg = player_history.nlargest(3, 'year')['position_numeric'].mean()

            if not pd.isna(recent_avg) and not pd.isna(older_avg):
                if recent_avg < older_avg:
                    st.success(f"📈 Improving trend: Recent avg finish {recent_avg:.1f} vs older {older_avg:.1f}")
                elif recent_avg > older_avg:
                    st.warning(f"📉 Declining trend: Recent avg finish {recent_avg:.1f} vs older {older_avg:.1f}")
                else:
                    st.info(f"➡️ Stable performance: Recent avg {recent_avg:.1f}")

    with tab2:
        # Bar chart of earnings
        fig2 = px.bar(
            player_history.sort_values('year'),
            x='year',
            y='earnings',
            title=f"{selected_player}'s Earnings History at {tournament_name}",
            labels={'year': 'Year', 'earnings': 'Earnings ($)'},
            color='earnings',
            color_continuous_scale='Greens'
        )

        st.plotly_chart(fig2, use_container_width=True)

        # Earnings summary
        career_earnings = player_history['earnings'].sum()
        earnings_text = f"${career_earnings:,.0f}" if pd.notna(career_earnings) and career_earnings > 0 else "N/A"
        st.metric("Career Earnings at This Event", earnings_text)

    with tab3:
        # Score analysis - only for made cuts
        made_cut_scores = player_history[player_history['made_cut']]

        if not made_cut_scores.empty:
            fig3 = px.line(
                made_cut_scores.sort_values('year'),
                x='year',
                y='score_to_par',
                title=f"{selected_player}'s Score Relative to Par (Made Cuts Only)",
                labels={'year': 'Year', 'score_to_par': 'Score to Par'},
                markers=True
            )

            # Add horizontal line at par (0)
            fig3.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Par")

            st.plotly_chart(fig3, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                best_score = made_cut_scores['score_to_par'].min()
                best_display = f"{int(best_score):+d}" if pd.notna(best_score) else "N/A"
                st.metric("Best Score to Par", best_display)
            with col2:
                avg_score = made_cut_scores['score_to_par'].mean()
                avg_display = f"{int(round(avg_score)):+d}" if pd.notna(avg_score) else "N/A"
                st.metric("Avg Score to Par", avg_display)
            with col3:
                latest_score = made_cut_scores.iloc[0]['score_to_par'] if len(made_cut_scores) > 0 else None
                latest_display = f"{int(latest_score):+d}" if pd.notna(latest_score) else "N/A"
                st.metric("Latest Score to Par", latest_display)
        else:
            st.info("No made cut data available - player has not completed a full tournament")

    # Performance insights
    st.divider()
    st.subheader("💡 Performance Insights")

    col1, col2 = st.columns(2)

    with col1:
        # Consistency analysis
        if len(player_history) >= 2:
            finish_std = player_history['position_numeric'].std()
            if not pd.isna(finish_std):
                if finish_std < 10:
                    st.success(f"🎯 Very consistent: Finish position variance of {finish_std:.1f}")
                elif finish_std < 20:
                    st.info(f"📊 Moderately consistent: Finish position variance of {finish_std:.1f}")
                else:
                    st.warning(f"🎲 Inconsistent: High variance of {finish_std:.1f}")

    with col2:
        # Recent vs career comparison
        if len(player_history) >= 5:
            recent_3 = player_history.nsmallest(3, 'year')['position_numeric'].mean()
            career_avg = player_history['position_numeric'].mean()

            if not pd.isna(recent_3) and not pd.isna(career_avg):
                diff = career_avg - recent_3
                if diff > 5:
                    st.success(f"🔥 Hot lately: {diff:.1f} positions better than career avg")
                elif diff < -5:
                    st.warning(f"❄️ Cold lately: {abs(diff):.1f} positions worse than career avg")
                else:
                    st.info(f"➡️ Performing at career average")

    # Quick action button
    st.divider()
    if selected_player not in used_players:
        if st.button(f"✅ Mark {selected_player} as Used", use_container_width=True, type="primary"):
            db.mark_player_used(selected_player, tournament_name, f"Week {datetime.now().isocalendar()[1]}")
            st.success(f"Marked {selected_player} as used!")
            st.rerun()
    else:
        if st.button(f"↩️ Remove {selected_player} from Used List", use_container_width=True):
            db.remove_used_player(selected_player)
            st.success(f"Removed {selected_player} from used list!")
            st.rerun()
