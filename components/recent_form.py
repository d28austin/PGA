"""
Recent Form Component
Shows player's recent tournament performance across all events
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
from datetime import datetime


def render_recent_form(db):
    """Render the recent form analysis view"""

    st.subheader("📈 Recent Form Analysis")
    st.markdown("Search for any player to see their recent tournament performance history")

    # Get all unique players from database
    conn = sqlite3.connect(db.db_path)
    all_players_df = pd.read_sql("""
        SELECT DISTINCT player_name
        FROM tournament_results
        WHERE player_name IS NOT NULL
        ORDER BY player_name
    """, conn)
    conn.close()

    if all_players_df.empty:
        st.warning("No player data available in the database")
        return

    # Player search/selection
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_player = st.selectbox(
            "Search for a player:",
            options=[""] + sorted(all_players_df['player_name'].unique()),
            help="Type to search or scroll to find a player"
        )

    with col2:
        if selected_player:
            used_players = db.get_used_players()
            if selected_player in used_players:
                st.error("🚫 Used")
            else:
                st.success("✅ Available")

    if not selected_player:
        st.info("👆 Select a player above to view their recent form")
        return

    st.divider()

    # Get player's complete tournament history
    conn = sqlite3.connect(db.db_path)
    player_history = pd.read_sql("""
        SELECT *
        FROM tournament_results
        WHERE player_name = ?
        AND position IS NOT NULL
        AND position != 'None'
        ORDER BY year DESC, tournament_name
    """, conn, params=(selected_player,))
    conn.close()

    if player_history.empty:
        st.warning(f"No tournament data found for {selected_player}")
        return

    # Clean and convert position data
    player_history['position_clean'] = player_history['position'].astype(str).str.replace('T', '').str.replace('T-', '')
    player_history['position_numeric'] = pd.to_numeric(player_history['position_clean'], errors='coerce')
    player_history['total_score_numeric'] = pd.to_numeric(player_history['total_score'], errors='coerce')
    player_history['earnings_numeric'] = pd.to_numeric(player_history['earnings'], errors='coerce')

    # Determine made cut (position <= 70 and reasonable score)
    player_history['made_cut'] = player_history['position_numeric'] <= 70

    # Summary stats
    st.subheader(f"🏌️ {selected_player} - Career Statistics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_events = len(player_history)
        st.metric("Total Events", total_events)

    with col2:
        made_cuts = player_history['made_cut'].sum()
        cut_pct = (made_cuts / total_events * 100) if total_events > 0 else 0
        st.metric("Made Cuts", f"{made_cuts} ({cut_pct:.0f}%)")

    with col3:
        avg_finish = player_history[player_history['made_cut']]['position_numeric'].mean()
        st.metric("Avg Finish", f"{avg_finish:.1f}" if not pd.isna(avg_finish) else "N/A")

    with col4:
        best_finish = player_history['position_numeric'].min()
        st.metric("Best Finish", f"{int(best_finish)}" if not pd.isna(best_finish) else "N/A")

    with col5:
        total_earnings = player_history['earnings_numeric'].sum()
        if pd.notna(total_earnings) and total_earnings > 0:
            st.metric("Career Earnings", f"${total_earnings:,.0f}")
        else:
            st.metric("Career Earnings", "N/A")

    # Recent performance table
    st.divider()
    st.subheader("📋 Recent Tournament Results")

    # Show filters
    col1, col2, col3 = st.columns(3)

    with col1:
        years_to_show = st.slider(
            "Years to display:",
            min_value=1,
            max_value=min(12, len(player_history['year'].unique())),
            value=min(3, len(player_history['year'].unique())),
            help="Select how many recent years to display"
        )

    with col2:
        show_only_made_cuts = st.checkbox("Made cuts only", value=False)

    with col3:
        tournament_filter = st.text_input("Filter by tournament:", "")

    # Apply filters
    recent_years = sorted(player_history['year'].unique(), reverse=True)[:years_to_show]
    filtered_history = player_history[player_history['year'].isin(recent_years)].copy()

    if show_only_made_cuts:
        filtered_history = filtered_history[filtered_history['made_cut']]

    if tournament_filter:
        filtered_history = filtered_history[
            filtered_history['tournament_name'].str.contains(tournament_filter, case=False, na=False)
        ]

    # Format for display
    display_history = filtered_history.sort_values(['year', 'tournament_name'], ascending=[False, True]).copy()
    display_history['earnings_display'] = display_history['earnings_numeric'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
    )

    st.dataframe(
        display_history[['year', 'tournament_name', 'position', 'total_score', 'earnings_display', 'made_cut']],
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "tournament_name": "Tournament",
            "position": "Finish",
            "total_score": st.column_config.NumberColumn("Score", format="%d"),
            "earnings_display": "Earnings",
            "made_cut": st.column_config.CheckboxColumn("Made Cut")
        },
        hide_index=True,
        use_container_width=True,
        height=500
    )

    # Performance visualizations
    st.divider()
    st.subheader("📊 Performance Trends")

    tab1, tab2, tab3 = st.tabs(["Finish Position Trend", "Yearly Summary", "Tournament Frequency"])

    with tab1:
        # Line chart of finishes over time (made cuts only)
        made_cut_history = player_history[player_history['made_cut']].sort_values(['year', 'tournament_name'])

        if not made_cut_history.empty:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=list(range(len(made_cut_history))),
                y=made_cut_history['position_numeric'],
                mode='lines+markers',
                name='Finish Position',
                text=made_cut_history['tournament_name'] + ' (' + made_cut_history['year'].astype(str) + ')',
                hovertemplate='<b>%{text}</b><br>Finish: %{y}<extra></extra>',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))

            fig.update_layout(
                title=f"{selected_player}'s Finish Positions (Made Cuts)",
                xaxis_title="Event Sequence",
                yaxis_title="Finish Position",
                yaxis=dict(autorange='reversed'),
                hovermode='closest',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No made cut data available")

    with tab2:
        # Yearly summary stats
        yearly_stats = player_history.groupby('year').agg({
            'tournament_name': 'count',
            'made_cut': 'sum',
            'position_numeric': lambda x: x[player_history.loc[x.index, 'made_cut']].mean() if any(player_history.loc[x.index, 'made_cut']) else None,
            'earnings_numeric': 'sum'
        }).reset_index()

        yearly_stats.columns = ['Year', 'Events Played', 'Cuts Made', 'Avg Finish', 'Total Earnings']
        yearly_stats = yearly_stats.sort_values('Year', ascending=False)

        # Format display
        yearly_display = yearly_stats.copy()
        yearly_display['Avg Finish'] = yearly_display['Avg Finish'].round(1)
        yearly_display['Total Earnings'] = yearly_display['Total Earnings'].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
        )
        yearly_display['Cut %'] = (yearly_display['Cuts Made'] / yearly_display['Events Played'] * 100).round(0).astype('Int64')

        st.dataframe(
            yearly_display[['Year', 'Events Played', 'Cuts Made', 'Cut %', 'Avg Finish', 'Total Earnings']],
            column_config={
                "Year": st.column_config.NumberColumn("Year", format="%d"),
                "Events Played": st.column_config.NumberColumn("Events", format="%d"),
                "Cuts Made": st.column_config.NumberColumn("Cuts", format="%d"),
                "Cut %": st.column_config.NumberColumn("Cut %", format="%d%%"),
                "Avg Finish": st.column_config.NumberColumn("Avg Finish", format="%.1f"),
                "Total Earnings": "Earnings"
            },
            hide_index=True,
            use_container_width=True
        )

    with tab3:
        # Tournament frequency - which tournaments played most
        tournament_freq = player_history.groupby('tournament_name').agg({
            'year': 'count',
            'made_cut': 'sum',
            'position_numeric': lambda x: x[player_history.loc[x.index, 'made_cut']].mean() if any(player_history.loc[x.index, 'made_cut']) else None,
            'earnings_numeric': 'sum'
        }).reset_index()

        tournament_freq.columns = ['Tournament', 'Times Played', 'Cuts Made', 'Avg Finish', 'Total Earnings']
        tournament_freq = tournament_freq.sort_values('Times Played', ascending=False)

        # Format display
        freq_display = tournament_freq.copy()
        freq_display['Avg Finish'] = freq_display['Avg Finish'].round(1)
        freq_display['Total Earnings'] = freq_display['Total Earnings'].apply(
            lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else ""
        )

        st.dataframe(
            freq_display.head(20),
            column_config={
                "Tournament": "Tournament",
                "Times Played": st.column_config.NumberColumn("Apps", format="%d"),
                "Cuts Made": st.column_config.NumberColumn("Cuts", format="%d"),
                "Avg Finish": st.column_config.NumberColumn("Avg", format="%.1f"),
                "Total Earnings": "Earnings"
            },
            hide_index=True,
            use_container_width=True
        )

        st.caption(f"Showing top 20 tournaments (out of {len(tournament_freq)} total)")

    # Quick action button
    st.divider()
    used_players = db.get_used_players()
    if selected_player not in used_players:
        if st.button(f"✅ Mark {selected_player} as Used", use_container_width=True, type="primary"):
            db.mark_player_used(selected_player, "Recent Form", f"Week {datetime.now().isocalendar()[1]}")
            st.success(f"Marked {selected_player} as used!")
            st.rerun()
    else:
        if st.button(f"↩️ Remove {selected_player} from Used List", use_container_width=True):
            db.remove_used_player(selected_player)
            st.success(f"Removed {selected_player} from used list!")
            st.rerun()
