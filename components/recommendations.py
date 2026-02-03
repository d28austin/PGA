"""
Enhanced Recommendations Component
Combines historical data with live betting odds for value analysis
Uses unified ValueCalculator with regression-optimized weights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
import sqlite3
from components.value_calculator import ValueCalculator


# Initialize shared value calculator
_value_calculator = ValueCalculator()


def calculate_enhanced_value(player_data: pd.Series, odds: Optional[float] = None) -> dict:
    """
    Wrapper function that uses unified ValueCalculator

    Uses enhanced regression model with 12 features:
    - OWGR: 28.9% importance (most important!)
    - Recent form: 44.3% combined (top 10 rate, avg finish, events)
    - Course history: 11.0%

    Model Performance:
    - Ridge R²: 0.097 (4x improvement)
    - Random Forest R²: 0.855
    - Correlation: 0.311 (was -0.031)

    Args:
        player_data: Series with player statistics
        odds: American odds (e.g., +450, -110)

    Returns:
        Dictionary with value metrics
    """
    result = _value_calculator.calculate_value(player_data, odds=odds)

    # Map to expected field names for backwards compatibility
    return {
        'final_value_score': result['final_value_score'],
        'base_value': result['base_value'],
        'history_component': result['history_score'],
        'form_component': result['form_score'],
        'course_component': result['course_fit_score'],
        'owgr_component': result.get('owgr_score', 0),
        'predicted_finish': result.get('predicted_finish'),
        'odds': result.get('odds'),
        'implied_probability': result.get('implied_probability'),
        'value_edge': result.get('value_edge'),
        'estimated_win_prob': result.get('estimated_win_prob'),
        'odds_adjustment': result.get('odds_adjustment', 0)
    }


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
    Display betting odds scraped from DraftKings

    Args:
        tournament_name: Name of the tournament
        db: Database instance
        fetcher: ESPN data fetcher
        odds_fetcher: Odds fetcher instance (optional)
    """
    st.header("💰 Betting Odds")

    # Info about the feature
    with st.expander("ℹ️ About This Data"):
        st.markdown("""
        This section displays betting odds scraped from DraftKings.

        **To update odds:**
        1. Run the weekly scraper: `python scrape_weekly_odds.py`
        2. Chrome will open and navigate to DraftKings
        3. Solve any CAPTCHA if prompted
        4. Scraper will pull all player odds
        5. Odds automatically save to database and appear here

        **Note:** Odds are scraped weekly, not live. Run the scraper before each tournament to get latest odds.
        """)

    # Initialize odds fetcher (no API key needed)
    from data.odds_fetcher import OddsFetcher
    odds_fetcher = OddsFetcher(api_key=None)

    # Get odds data from scraped database only
    odds_df = None
    scraped_time = None

    with st.spinner("Loading betting odds..."):
        # Only check for scraped odds in database
        odds_df = odds_fetcher.get_scraped_odds_from_db(tournament_name)

        if not odds_df.empty:
            scraped_time = pd.to_datetime(odds_df['scraped_at'].iloc[0]).strftime('%B %d, %Y at %I:%M %p')

    # Display odds status and data
    if not odds_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success(f"📊 Odds Available")
            st.caption(f"Last updated: {scraped_time}")

        with col2:
            bookmakers = odds_df['bookmaker'].unique()
            st.metric("Bookmakers", len(bookmakers))
            st.caption(", ".join(bookmakers))

        with col3:
            st.metric("Players with Odds", odds_df['player_name'].nunique())

        st.markdown("---")

        # Prepare odds data for display
        display_df = odds_df.copy()

        # Sort by odds (favorites at top - lowest odds numbers)
        display_df['odds_numeric'] = pd.to_numeric(display_df['odds'], errors='coerce')
        display_df = display_df.sort_values('odds_numeric', ascending=True)

        # Display odds table
        st.dataframe(
            display_df[['player_name', 'odds', 'bookmaker']],
            column_config={
                "player_name": st.column_config.TextColumn("Player", width="medium"),
                "odds": st.column_config.NumberColumn("Odds", format="%+d", help="American odds format (+150 = underdog, -110 = favorite)"),
                "bookmaker": st.column_config.TextColumn("Bookmaker", width="small")
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
    else:
        st.warning(f"⚠️ No odds available for '{tournament_name}'")
        st.info(f"💡 Run the weekly scraper to get odds:\n```bash\npython scrape_weekly_odds.py\n```")
        st.markdown("The scraper will:")
        st.markdown("- Open Chrome and navigate to DraftKings")
        st.markdown("- Let you solve any CAPTCHA")
        st.markdown("- Scrape all player odds")
        st.markdown("- Save to database (available here instantly)")
        st.markdown("---")
        st.markdown("**Note:** Analysis will continue with historical data only (no odds-based metrics).")
