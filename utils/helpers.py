"""
Utility helper functions
"""

import pandas as pd
from typing import List, Dict


def clean_position_data(position_series: pd.Series) -> pd.Series:
    """
    Clean position data, converting strings like 'T5' to numeric

    Args:
        position_series: Series containing position data

    Returns:
        Series with numeric position values
    """
    def convert_position(pos):
        if pd.isna(pos):
            return None

        pos_str = str(pos).upper()

        # Remove 'T' for tied positions
        if pos_str.startswith('T'):
            pos_str = pos_str[1:]

        # Handle special cases
        if pos_str in ['CUT', 'WD', 'DQ', 'MDF']:
            return None

        try:
            return float(pos_str)
        except ValueError:
            return None

    return position_series.apply(convert_position)


def calculate_consistency_score(finishes: List[float]) -> float:
    """
    Calculate a consistency score based on standard deviation of finishes
    Lower score = more consistent

    Args:
        finishes: List of finish positions

    Returns:
        Consistency score
    """
    if not finishes or len(finishes) < 2:
        return 0.0

    return pd.Series(finishes).std()


def get_form_rating(recent_finishes: List[float]) -> str:
    """
    Get a rating of recent form based on finishes

    Args:
        recent_finishes: List of recent finish positions

    Returns:
        Form rating string
    """
    if not recent_finishes:
        return "Unknown"

    avg = sum(recent_finishes) / len(recent_finishes)

    if avg <= 10:
        return "🔥 Excellent"
    elif avg <= 20:
        return "✅ Good"
    elif avg <= 35:
        return "➡️ Average"
    else:
        return "❄️ Cold"


def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"${amount:,.0f}"


def get_trend_indicator(recent_avg: float, historical_avg: float) -> tuple:
    """
    Get trend indicator comparing recent to historical performance

    Args:
        recent_avg: Recent average finish
        historical_avg: Historical average finish

    Returns:
        Tuple of (indicator_emoji, description)
    """
    diff = historical_avg - recent_avg

    if diff > 5:
        return ("📈", f"Improving (+{diff:.1f})")
    elif diff < -5:
        return ("📉", f"Declining ({diff:.1f})")
    else:
        return ("➡️", "Stable")


def filter_available_players(players_df: pd.DataFrame, used_players: List[str]) -> pd.DataFrame:
    """
    Filter out used players from a dataframe

    Args:
        players_df: DataFrame with player information
        used_players: List of used player names

    Returns:
        Filtered DataFrame
    """
    return players_df[~players_df['player_name'].isin(used_players)]
