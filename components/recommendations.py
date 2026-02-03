"""
Enhanced Recommendations Component
Combines historical data with live betting odds for value analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
import sqlite3


def calculate_enhanced_value(player_data: pd.Series, odds: Optional[float] = None) -> dict:
    """
    Calculate enhanced value score incorporating betting odds

    Args:
        player_data: Series with player statistics
        odds: American odds (e.g., +450, -110)

    Returns:
        Dictionary with value metrics
    """
    # Historical performance metrics (0-100 scale)
    history_score = 0
    recent_form_score = 0
    course_fit_score = 0

    # Historical wins/top 10s at this course
    if 'wins' in player_data and player_data.get('wins', 0) > 0:
        history_score += 30
    if 'top_10s' in player_data:
        top_10_rate = player_data.get('top_10s', 0) / max(player_data.get('events', 1), 1)
        history_score += min(top_10_rate * 100, 40)

    # Recent form (last 5-10 events)
    if 'recent_avg_finish' in player_data:
        avg_finish = player_data.get('recent_avg_finish', 70)
        if avg_finish <= 10:
            recent_form_score = 40
        elif avg_finish <= 20:
            recent_form_score = 30
        elif avg_finish <= 30:
            recent_form_score = 20
        else:
            recent_form_score = 10

    # Course fit (strokes gained, scoring average, etc.)
    if 'avg_score' in player_data and 'par' in player_data:
        scoring = player_data.get('avg_score', 72)
        par = player_data.get('par', 72)
        if scoring < par:
            course_fit_score = min((par - scoring) * 10, 30)

    base_value = history_score + recent_form_score + course_fit_score

    result = {
        'base_value': base_value,
        'history_component': history_score,
        'form_component': recent_form_score,
        'course_component': course_fit_score
    }

    # Add odds-based metrics if available
    if odds is not None:
        implied_prob = american_to_probability(odds)
        decimal_odds = american_to_decimal(odds)

        # Estimate win probability from base value (rough approximation)
        estimated_win_prob = base_value / 500  # Scale to reasonable probability

        # Calculate value edge
        value_edge = ((estimated_win_prob - implied_prob) / implied_prob) * 100 if implied_prob > 0 else 0

        result.update({
            'odds': odds,
            'implied_probability': implied_prob,
            'decimal_odds': decimal_odds,
            'estimated_win_prob': estimated_win_prob,
            'value_edge': value_edge,
            'final_value_score': base_value + (value_edge * 2)  # Weight the edge
        })
    else:
        result['final_value_score'] = base_value

    return result


def american_to_probability(american_odds: int) -> float:
    """Convert American odds to implied probability"""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def render_recommendations(tournament_name: str, db, fetcher, odds_fetcher=None):
    """
    Render enhanced recommendations with betting odds integration

    Args:
        tournament_name: Name of the tournament
        db: Database instance
        fetcher: ESPN data fetcher
        odds_fetcher: Odds fetcher instance (optional)
    """
    st.header("🎯 Enhanced Recommendations")

    # Info about the feature
    with st.expander("ℹ️ How This Works"):
        st.markdown("""
        This recommendation system combines:
        - **Historical Performance**: Past results at this tournament
        - **Recent Form**: Performance in last 10 events
        - **Course Fit**: Scoring average and stats at this venue
        - **Betting Odds** (when available): Live market prices for value analysis

        **Value Score**: Higher = Better pick
        - 70+: Excellent value
        - 50-70: Good value
        - 30-50: Fair value
        - <30: Poor value

        **Value Edge**: Shows if a player is underpriced by bookmakers
        - Positive % = Good betting value
        - Negative % = Overpriced
        """)

    # API Key input for odds
    st.subheader("Betting Odds Integration")

    col1, col2 = st.columns([2, 1])

    with col1:
        api_key = st.text_input(
            "The Odds API Key (optional - get free key at the-odds-api.com)",
            type="password",
            help="Enter your API key to fetch live betting odds. Free tier: 500 requests/month"
        )

    with col2:
        use_sample_data = st.checkbox("Use Sample Odds Data", value=True,
                                      help="Test with sample data if you don't have an API key")

    # Initialize odds fetcher if we have a key or want sample data
    if api_key or use_sample_data:
        from data.odds_fetcher import OddsFetcher
        odds_fetcher = OddsFetcher(api_key=api_key if api_key else None)

        if use_sample_data:
            st.info("📊 Using sample betting odds data for demonstration")
        else:
            st.success("✅ Connected to betting odds API")

    st.markdown("---")

    # Get tournament field
    conn = sqlite3.connect(db.db_path)

    # Query to get players in this tournament with their historical stats
    query = """
        SELECT
            tr.player_name,
            COUNT(DISTINCT tr.year) as events,
            SUM(CASE WHEN CAST(tr.position AS INTEGER) = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN CAST(tr.position AS INTEGER) <= 10 THEN 1 ELSE 0 END) as top_10s,
            AVG(CASE
                WHEN tr.position NOT LIKE '%WD%'
                AND tr.position NOT LIKE '%DQ%'
                AND tr.position NOT LIKE '%CUT%'
                THEN CAST(tr.position AS INTEGER)
            END) as avg_finish,
            AVG(tr.total_score) as avg_score
        FROM tournament_results tr
        WHERE tr.tournament_name = ?
        GROUP BY tr.player_name
        HAVING events >= 1
        ORDER BY wins DESC, top_10s DESC, avg_finish ASC
    """

    players_df = pd.read_sql(query, conn, params=(tournament_name,))
    conn.close()

    if players_df.empty:
        st.warning(f"No historical data found for {tournament_name}")
        return

    # Get odds data if available
    odds_df = None
    if odds_fetcher:
        with st.spinner("Fetching live betting odds..."):
            odds_df = odds_fetcher._get_sample_odds()  # Using sample for now

            if not odds_df.empty:
                # Get best odds for each player
                best_odds = odds_df.groupby('player_name').agg({
                    'odds': 'mean'
                }).reset_index()
                best_odds.columns = ['player_name', 'avg_odds']

                # Merge with players data
                players_df = players_df.merge(best_odds, on='player_name', how='left')

    # Calculate value scores for all players
    value_scores = []

    for _, player in players_df.iterrows():
        odds = player.get('avg_odds', None)
        value = calculate_enhanced_value(player, odds)

        value_scores.append({
            'player_name': player['player_name'],
            'events': player['events'],
            'wins': player['wins'],
            'top_10s': player['top_10s'],
            'avg_finish': player.get('avg_finish', 0),
            'value_score': value['final_value_score'],
            'history_score': value['history_component'],
            'form_score': value['form_component'],
            'course_score': value['course_component'],
            'odds': odds,
            'implied_prob': value.get('implied_probability', None),
            'value_edge': value.get('value_edge', None)
        })

    value_df = pd.DataFrame(value_scores)
    value_df = value_df.sort_values('value_score', ascending=False)

    # Display top recommendations
    st.subheader("🏆 Top Value Picks")

    # Top 10 recommendations
    top_picks = value_df.head(10).copy()

    # Format for display
    display_df = top_picks.copy()
    display_df['value_score'] = display_df['value_score'].round(1)
    display_df['avg_finish'] = display_df['avg_finish'].round(1)

    if 'odds' in display_df.columns and display_df['odds'].notna().any():
        display_df['odds'] = display_df['odds'].apply(lambda x: f"+{int(x)}" if pd.notna(x) and x > 0 else f"{int(x)}" if pd.notna(x) else "N/A")
        display_df['implied_prob'] = display_df['implied_prob'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        display_df['value_edge'] = display_df['value_edge'].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")

    # Style the dataframe
    st.dataframe(
        display_df[['player_name', 'value_score', 'events', 'wins', 'top_10s',
                   'avg_finish', 'odds', 'implied_prob', 'value_edge']],
        column_config={
            'player_name': st.column_config.TextColumn("Player", width="medium"),
            'value_score': st.column_config.NumberColumn("Value Score", width="small", help="Higher = Better"),
            'events': st.column_config.NumberColumn("Events", width="small"),
            'wins': st.column_config.NumberColumn("Wins", width="small"),
            'top_10s': st.column_config.NumberColumn("Top 10s", width="small"),
            'avg_finish': st.column_config.NumberColumn("Avg Finish", width="small"),
            'odds': st.column_config.TextColumn("Odds", width="small", help="American odds"),
            'implied_prob': st.column_config.TextColumn("Win %", width="small", help="Implied probability"),
            'value_edge': st.column_config.TextColumn("Edge", width="small", help="Value vs odds")
        },
        use_container_width=True,
        hide_index=True
    )

    # Visualizations
    st.markdown("---")
    st.subheader("📊 Value Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Value score breakdown
        fig = go.Figure()

        top_5 = top_picks.head(5)

        fig.add_trace(go.Bar(
            name='History',
            x=top_5['player_name'],
            y=top_5['history_score'],
            marker_color='lightblue'
        ))
        fig.add_trace(go.Bar(
            name='Form',
            x=top_5['player_name'],
            y=top_5['form_score'],
            marker_color='lightgreen'
        ))
        fig.add_trace(go.Bar(
            name='Course Fit',
            x=top_5['player_name'],
            y=top_5['course_score'],
            marker_color='lightyellow'
        ))

        fig.update_layout(
            title="Value Score Components (Top 5)",
            xaxis_title="Player",
            yaxis_title="Score",
            barmode='stack',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Value vs Odds (if available)
        if 'value_edge' in value_df.columns and value_df['value_edge'].notna().any():
            fig = px.scatter(
                value_df.head(20),
                x='implied_prob',
                y='value_score',
                size='top_10s',
                color='value_edge',
                hover_data=['player_name', 'wins', 'avg_finish'],
                title="Value Score vs Implied Win Probability",
                labels={
                    'implied_prob': 'Implied Win Probability',
                    'value_score': 'Value Score',
                    'value_edge': 'Value Edge %'
                },
                color_continuous_scale='RdYlGn',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            # Alternative chart without odds
            fig = px.bar(
                top_picks.head(10),
                x='player_name',
                y='value_score',
                color='value_score',
                color_continuous_scale='Viridis',
                title="Top 10 Value Scores",
                labels={'player_name': 'Player', 'value_score': 'Value Score'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # Export recommendations
    st.markdown("---")
    if st.button("📥 Export Recommendations to CSV"):
        csv = value_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{tournament_name.replace(' ', '_')}_recommendations.csv",
            mime="text/csv"
        )
