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

    # Check for API key in secrets first
    api_key_from_secrets = None
    try:
        if hasattr(st, 'secrets') and 'odds_api' in st.secrets:
            api_key_from_secrets = st.secrets['odds_api']['api_key']
    except:
        pass

    col1, col2 = st.columns([2, 1])

    with col1:
        if api_key_from_secrets:
            st.success("🔑 API Key loaded from secrets")
            api_key = api_key_from_secrets
            use_live_odds = st.checkbox("Use Live Odds", value=True,
                                       help="Uncheck to use sample data instead")
        else:
            api_key = st.text_input(
                "The Odds API Key (optional - get free key at the-odds-api.com)",
                type="password",
                help="Enter your API key to fetch live betting odds. Free tier: 500 requests/month"
            )
            use_live_odds = bool(api_key)

    with col2:
        if api_key_from_secrets:
            use_sample_data = not use_live_odds
        else:
            use_sample_data = st.checkbox("Use Sample Odds Data", value=True,
                                          help="Test with sample data if you don't have an API key")

    # Initialize odds fetcher if we have a key or want sample data
    if api_key or use_sample_data:
        from data.odds_fetcher import OddsFetcher

        if use_sample_data:
            odds_fetcher = OddsFetcher(api_key=None)
            st.info("📊 Using sample betting odds data for demonstration")
        else:
            odds_fetcher = OddsFetcher(api_key=api_key)
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
    odds_source = None

    if odds_fetcher:
        with st.spinner("Loading betting odds..."):
            # Try to fetch odds for this specific tournament
            if use_sample_data:
                odds_df = odds_fetcher._get_sample_odds(tournament_name)
                odds_source = "sample_data"
            else:
                odds_df = odds_fetcher.get_tournament_odds(tournament_name)

                if not odds_df.empty:
                    # Determine the source
                    if 'scraped_at' in odds_df.columns:
                        odds_source = "scraped"
                        scraped_time = pd.to_datetime(odds_df['scraped_at'].iloc[0]).strftime('%B %d, %Y at %I:%M %p')
                    else:
                        odds_source = "live_api"
                else:
                    st.warning(f"No odds available for '{tournament_name}'.")
                    odds_df = odds_fetcher._get_sample_odds(tournament_name)
                    odds_source = "sample_data"

    # Display odds source info
    if odds_df is not None and not odds_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            if odds_source == "scraped":
                st.success(f"📊 Using Scraped Odds")
                st.caption(f"Last updated: {scraped_time}")
            elif odds_source == "live_api":
                st.success(f"🔴 Using Live API Odds")
            else:
                st.info(f"📝 Using Sample Odds")
                st.caption("Run scraper for live data")

        with col2:
            bookmakers = odds_df['bookmaker'].unique()
            st.metric("Bookmakers", len(bookmakers))
            st.caption(", ".join(bookmakers))

        with col3:
            st.metric("Players with Odds", odds_df['player_name'].nunique())

    # Merge odds with historical data
    if odds_df is not None and not odds_df.empty:
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

    # Add filter options
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        show_option = st.radio(
            "Show Players",
            ["With Odds Only", "All Players", "Without Odds"],
            help="Filter based on odds availability"
        )

    with col2:
        min_events = st.slider(
            "Min Events at Course",
            min_value=1,
            max_value=int(value_df['events'].max()) if not value_df.empty else 10,
            value=1,
            help="Minimum number of times played this tournament"
        )

    with col3:
        sort_by = st.selectbox(
            "Sort By",
            ["Value Score", "Value Edge", "Recent Odds", "Historical Wins"],
            help="How to rank players"
        )

    # Apply filters
    filtered_df = value_df.copy()

    if show_option == "With Odds Only":
        filtered_df = filtered_df[filtered_df['odds'].notna()]
    elif show_option == "Without Odds":
        filtered_df = filtered_df[filtered_df['odds'].isna()]

    filtered_df = filtered_df[filtered_df['events'] >= min_events]

    # Apply sorting
    if sort_by == "Value Score":
        filtered_df = filtered_df.sort_values('value_score', ascending=False)
    elif sort_by == "Value Edge":
        filtered_df = filtered_df.sort_values('value_edge', ascending=False)
    elif sort_by == "Recent Odds":
        filtered_df = filtered_df.sort_values('odds', ascending=True)
    elif sort_by == "Historical Wins":
        filtered_df = filtered_df.sort_values('wins', ascending=False)

    if filtered_df.empty:
        st.warning("No players match your filters. Try adjusting the criteria.")
        return

    # Display top recommendations
    st.markdown("---")
    st.subheader("🏆 Top Value Picks")

    # Show top 15
    top_picks = filtered_df.head(15).copy()

    # Add top 3 detailed recommendations
    if len(top_picks) >= 3:
        st.markdown("### 🎯 Top 3 Recommendations with Analysis")

        for i in range(min(3, len(top_picks))):
            player = top_picks.iloc[i]

            with st.expander(f"#{i+1}: {player['player_name']} - Value Score: {player['value_score']:.1f}", expanded=(i==0)):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown("**Why This Pick:**")

                    reasons = []

                    # Historical performance
                    if player['wins'] > 0:
                        reasons.append(f"✅ {int(player['wins'])} win(s) at this tournament")
                    if player['top_10s'] >= 3:
                        reasons.append(f"✅ {int(player['top_10s'])} top 10 finishes")
                    if player['avg_finish'] <= 20 and player['avg_finish'] > 0:
                        reasons.append(f"✅ Strong avg finish: {player['avg_finish']:.1f}")

                    # Odds value
                    if pd.notna(player['odds']) and pd.notna(player['value_edge']):
                        if player['value_edge'] > 20:
                            reasons.append(f"✅ Excellent value: {player['value_edge']:+.1f}% edge over market")
                        elif player['value_edge'] > 0:
                            reasons.append(f"✅ Positive value: {player['value_edge']:+.1f}% edge")
                        else:
                            reasons.append(f"⚠️ Overpriced by market: {player['value_edge']:+.1f}%")

                    # Experience
                    if player['events'] >= 5:
                        reasons.append(f"✅ Experienced: {int(player['events'])} appearances")

                    for reason in reasons:
                        st.markdown(reason)

                with col2:
                    if pd.notna(player['odds']):
                        st.metric("Odds", f"+{int(player['odds'])}" if player['odds'] > 0 else f"{int(player['odds'])}")
                        st.metric("Win %", f"{player['implied_prob']*100:.1f}%")
                        st.metric("Edge", f"{player['value_edge']:+.1f}%")
                    else:
                        st.info("No odds available")

                    st.metric("Avg Finish", f"{player['avg_finish']:.1f}")
                    st.metric("Events", int(player['events']))

        st.markdown("---")

    # Format for display
    display_df = top_picks.copy()
    display_df['value_score'] = display_df['value_score'].round(1)
    display_df['avg_finish'] = display_df['avg_finish'].round(1)

    # Format odds columns
    if 'odds' in display_df.columns and display_df['odds'].notna().any():
        display_df['odds_display'] = display_df['odds'].apply(
            lambda x: f"+{int(x)}" if pd.notna(x) and x > 0 else f"{int(x)}" if pd.notna(x) else "—"
        )
        display_df['implied_prob_display'] = display_df['implied_prob'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—"
        )
        display_df['value_edge_display'] = display_df['value_edge'].apply(
            lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
        )
    else:
        display_df['odds_display'] = "—"
        display_df['implied_prob_display'] = "—"
        display_df['value_edge_display'] = "—"

    # Determine which columns to show based on odds availability
    has_odds = display_df['odds'].notna().any()

    if has_odds:
        columns_to_show = ['player_name', 'value_score', 'odds_display', 'implied_prob_display',
                          'value_edge_display', 'wins', 'top_10s', 'avg_finish', 'events']
        column_labels = {
            'player_name': 'Player',
            'value_score': 'Value',
            'odds_display': 'Odds',
            'implied_prob_display': 'Win %',
            'value_edge_display': 'Edge',
            'wins': 'Wins',
            'top_10s': 'Top 10s',
            'avg_finish': 'Avg',
            'events': 'Evts'
        }
    else:
        columns_to_show = ['player_name', 'value_score', 'wins', 'top_10s', 'avg_finish', 'events']
        column_labels = {
            'player_name': 'Player',
            'value_score': 'Value Score',
            'wins': 'Wins',
            'top_10s': 'Top 10s',
            'avg_finish': 'Avg Finish',
            'events': 'Events'
        }

    # Rename columns for display
    display_df_final = display_df[columns_to_show].copy()
    display_df_final.columns = [column_labels[col] for col in columns_to_show]

    # Style the dataframe
    st.dataframe(
        display_df_final,
        use_container_width=True,
        hide_index=True,
        height=600
    )

    # Add legend
    st.caption("""
    **Value Score**: Combined metric (history + form + course fit + odds value)
    **Edge**: Your advantage over market odds (positive = underpriced, negative = overpriced)
    **Avg**: Average finish position at this tournament
    """)

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
