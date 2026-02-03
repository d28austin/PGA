"""
Unified Value Calculator
Regression-optimized value calculation using all available historical data
"""

import pandas as pd
import numpy as np
import sqlite3
from typing import Optional, Dict


class ValueCalculator:
    """
    Calculates player value using regression-optimized weights

    Based on backtesting analysis that identified:
    - Average finish at course: 66.3% importance (DOMINANT)
    - Experience at course: 15.7% importance
    - Top 10 consistency: 12.9% importance
    - Wins: 5.1% importance
    """

    def __init__(self, db_path: str = "data/cache/pga_data.db"):
        self.db_path = db_path

        # Enhanced Ridge regression coefficients from backtesting
        # Trained on WM Phoenix Open 2020-2024 (397 players, R²=0.097)
        # Random Forest achieved R²=0.855 showing potential for non-linear modeling
        self.feature_names = [
            'prior_avg_finish', 'prior_wins', 'prior_top10s', 'prior_events',
            'prior_cut_rate', 'prior_top10_rate', 'prior_best_finish',
            'recent_avg_finish', 'recent_events', 'recent_cut_rate',
            'recent_top10_rate', 'owgr_ranking'
        ]

        self.coefficients = {
            'prior_avg_finish': 1.8511630549724232,
            'prior_wins': -2.0406458121277065,
            'prior_top10s': 5.941535299573351,
            'prior_events': -8.172405322613939,
            'prior_cut_rate': 0.0,
            'prior_top10_rate': 2.2981963652079913,
            'prior_best_finish': -0.5107832764315458,
            'recent_avg_finish': 15.76525823589875,  # MOST IMPORTANT!
            'recent_events': 1.9473153453755414,
            'recent_cut_rate': -1.159136266168197,
            'recent_top10_rate': 10.818779290972474,  # SECOND MOST IMPORTANT!
            'owgr_ranking': 3.9933167025990715
        }

        self.intercept = 45.042821158690174

        # Standardization parameters (actual means and std devs from training)
        self.means = {
            'prior_avg_finish': 16.66766222861941,
            'prior_wins': 0.06297229219143577,
            'prior_top10s': 3.1032745591939546,
            'prior_events': 4.138539042821159,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.6978019671344609,
            'prior_best_finish': 6.105793450881612,
            'recent_avg_finish': 28.77727525071167,
            'recent_events': 37.87909319899244,
            'recent_cut_rate': 0.9874055415617129,
            'recent_top10_rate': 0.42518736114443056,
            'owgr_ranking': 587.4307304785895
        }

        self.stds = {
            'prior_avg_finish': 20.437610112410706,
            'prior_wins': 0.30703626208445844,
            'prior_top10s': 2.1497851471775755,
            'prior_events': 2.3526502300382077,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.32576929375748853,
            'prior_best_finish': 18.451212589770467,
            'recent_avg_finish': 18.526183831550174,
            'recent_events': 10.47777983212367,
            'recent_cut_rate': 0.11151608877168089,
            'recent_top10_rate': 0.35213750908401287,
            'owgr_ranking': 876.397232527341
        }

    def calculate_value(
        self,
        player_data: pd.Series,
        tournament_name: Optional[str] = None,
        odds: Optional[float] = None
    ) -> Dict:
        """
        Calculate comprehensive value score for a player

        Args:
            player_data: Series with player statistics
            tournament_name: Tournament name (for getting additional context)
            odds: American odds (e.g., +450, -110) if available

        Returns:
            Dictionary with value metrics and components
        """
        # Extract all available features
        # Tournament-specific
        prior_events = player_data.get('events', 0) or player_data.get('appearances', 0) or 0
        prior_wins = player_data.get('wins', 0) or 0
        prior_top10s = player_data.get('top_10s', 0) or 0
        prior_avg_finish = player_data.get('avg_finish', None)
        prior_best_finish = player_data.get('best_finish', 999)
        prior_made_cuts = player_data.get('made_cuts', prior_events)  # Assume all if not specified

        # Calculate derived features
        prior_cut_rate = prior_made_cuts / prior_events if prior_events > 0 else 1.0
        prior_top10_rate = prior_top10s / prior_events if prior_events > 0 else 0.0

        # Recent overall form
        recent_avg_finish = player_data.get('recent_avg_finish', None)
        recent_events = player_data.get('recent_events', 0)
        recent_made_cuts = player_data.get('recent_made_cuts', recent_events)
        recent_top10s_count = player_data.get('recent_top10s', 0)

        recent_cut_rate = recent_made_cuts / recent_events if recent_events > 0 else 0.99
        recent_top10_rate = recent_top10s_count / recent_events if recent_events > 0 else 0.0

        # OWGR
        owgr_ranking = player_data.get('owgr_numeric', 999) or player_data.get('owgr', 999)

        # Initialize component scores
        course_fit_score = 0
        history_score = 0
        recent_form_score = 0

        # COMPREHENSIVE REGRESSION-BASED PREDICTION
        if prior_events > 0:
            # Build feature vector with ALL features
            features = {}

            # Tournament-specific features
            features['prior_avg_finish'] = prior_avg_finish if pd.notna(prior_avg_finish) else self.means['prior_avg_finish']
            features['prior_wins'] = prior_wins
            features['prior_top10s'] = prior_top10s
            features['prior_events'] = prior_events
            features['prior_cut_rate'] = prior_cut_rate
            features['prior_top10_rate'] = prior_top10_rate
            features['prior_best_finish'] = prior_best_finish if prior_best_finish < 999 else self.means['prior_best_finish']

            # Recent form features (use defaults if not available)
            features['recent_avg_finish'] = recent_avg_finish if pd.notna(recent_avg_finish) else self.means['recent_avg_finish']
            features['recent_events'] = recent_events if recent_events > 0 else self.means['recent_events']
            features['recent_cut_rate'] = recent_cut_rate
            features['recent_top10_rate'] = recent_top10_rate

            # OWGR
            features['owgr_ranking'] = owgr_ranking if owgr_ranking < 999 else self.means['owgr_ranking']

            # Standardize all features (z-score normalization)
            standardized = {}
            for name in self.feature_names:
                standardized[name] = (features[name] - self.means[name]) / self.stds[name]

            # Predict finish position using Ridge regression
            predicted_finish = self.intercept
            for name in self.feature_names:
                predicted_finish += self.coefficients[name] * standardized[name]

            # Convert predicted finish to value score (0-100 scale)
            # 1st place = 100 points, 50th place = 0 points
            course_fit_score = max(0, min(100, 100 - (predicted_finish * 2)))

            # COMPONENT BREAKDOWN (for interpretability)
            # Based on enhanced model: OWGR (28.9%) + Recent Form (44.3%) + Course History (11.0%)

            # OWGR component (current skill level - most important single feature)
            if owgr_ranking < 999:
                if owgr_ranking <= 10:
                    owgr_score = 30
                elif owgr_ranking <= 50:
                    owgr_score = 25
                elif owgr_ranking <= 100:
                    owgr_score = 20
                else:
                    owgr_score = max(0, 15 - (owgr_ranking / 50))
            else:
                owgr_score = 5

            # Recent form component
            if pd.notna(recent_avg_finish) and recent_avg_finish < 999:
                if recent_avg_finish <= 15:
                    recent_form_score = 35
                elif recent_avg_finish <= 25:
                    recent_form_score = 25
                elif recent_avg_finish <= 35:
                    recent_form_score = 15
                else:
                    recent_form_score = 10
                # Boost for top 10 rate
                recent_form_score += min(recent_top10_rate * 30, 15)
            else:
                recent_form_score = 10

            # Tournament history component
            if pd.notna(prior_avg_finish):
                if prior_avg_finish <= 10:
                    history_score = 30
                elif prior_avg_finish <= 20:
                    history_score = 25
                elif prior_avg_finish <= 30:
                    history_score = 20
                else:
                    history_score = 10
                # Wins boost
                if prior_wins > 0:
                    history_score += min(prior_wins * 10, 15)
                # Top 10 consistency
                history_score += min(prior_top10_rate * 15, 10)
            else:
                history_score = 5


        else:
            # No tournament history - rely on OWGR and recent form
            course_fit_score = 20  # Low baseline

            # Emphasize OWGR when no course history
            if owgr_ranking < 999:
                if owgr_ranking <= 50:
                    owgr_score = 30
                elif owgr_ranking <= 100:
                    owgr_score = 25
                else:
                    owgr_score = 20
            else:
                owgr_score = 10

            # Emphasize recent form when no course history
            if pd.notna(recent_avg_finish) and recent_avg_finish < 999:
                if recent_avg_finish <= 20:
                    recent_form_score = 30
                elif recent_avg_finish <= 30:
                    recent_form_score = 25
                else:
                    recent_form_score = 15
            else:
                recent_form_score = 10

            history_score = 5  # Minimal since no history

        # WEIGHTED COMBINATION
        # Weights based on Random Forest feature importance:
        # - OWGR: 28.9%, Recent form: 44.3%, Course history: 11%
        base_value = (
            course_fit_score * 0.45 +   # 45% - Regression prediction (integrates all 12 features)
            owgr_score * 0.30 +          # 30% - Current skill level
            recent_form_score * 0.20 +   # 20% - Recent overall form
            history_score * 0.05         # 5% - Tournament-specific bonus
        )

        result = {
            'base_value': base_value,
            'course_fit_score': course_fit_score,
            'history_score': history_score,
            'form_score': recent_form_score,
            'owgr_score': owgr_score,
            'predicted_finish': 100 - (course_fit_score / 2) if prior_events > 0 else None
        }

        # ADD ODDS-BASED METRICS (if available)
        if odds is not None and pd.notna(odds):
            implied_prob = self._american_to_probability(odds)

            # Estimate win probability from predicted finish
            if prior_events > 0 and pd.notna(prior_avg_finish):
                predicted_finish_pos = 100 - (course_fit_score / 2)

                # Win probability lookup based on predicted finish
                if predicted_finish_pos <= 5:
                    estimated_win_prob = 0.20
                elif predicted_finish_pos <= 10:
                    estimated_win_prob = 0.10
                elif predicted_finish_pos <= 15:
                    estimated_win_prob = 0.05
                elif predicted_finish_pos <= 25:
                    estimated_win_prob = 0.02
                elif predicted_finish_pos <= 40:
                    estimated_win_prob = 0.01
                else:
                    estimated_win_prob = 0.005

                # Adjust based on actual win rate
                win_rate = prior_wins / prior_events if prior_events > 0 else 0
                estimated_win_prob = (estimated_win_prob * 0.7) + (win_rate * 0.3)
                estimated_win_prob = max(0.001, min(estimated_win_prob, 0.30))
            else:
                estimated_win_prob = base_value / 2000
                estimated_win_prob = max(0.001, min(estimated_win_prob, 0.05))

            # Calculate value edge
            if implied_prob > 0.001:
                if implied_prob < 0.02:  # Long odds
                    value_edge = (estimated_win_prob - implied_prob) * 1000
                else:
                    value_edge = ((estimated_win_prob - implied_prob) / implied_prob) * 100
                value_edge = max(-100, min(value_edge, 200))
            else:
                value_edge = 0

            # Odds adjustment
            odds_adjustment = 0
            if value_edge > 50:
                odds_adjustment = 15
            elif value_edge > 20:
                odds_adjustment = 10
            elif value_edge > 0:
                odds_adjustment = 5
            elif value_edge < -50:
                odds_adjustment = -15
            elif value_edge < -20:
                odds_adjustment = -10
            elif value_edge < 0:
                odds_adjustment = -5

            final_value = base_value + odds_adjustment

            result.update({
                'odds': odds,
                'implied_probability': implied_prob,
                'estimated_win_prob': estimated_win_prob,
                'value_edge': value_edge,
                'odds_adjustment': odds_adjustment,
                'final_value_score': final_value
            })
        else:
            result['final_value_score'] = base_value

        return result

    def get_player_season_stats(self, player_name: str, year: int = 2024) -> Dict:
        """
        Get ESPN season statistics for a player

        Args:
            player_name: Player name
            year: Season year

        Returns:
            Dictionary with stat_category -> stat_value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT stat_category, stat_value
                FROM player_stats
                WHERE player_name = ?
                AND year = ?
            """
            df = pd.read_sql(query, conn, params=(player_name, year))
            conn.close()

            # Convert to dictionary
            stats = {row['stat_category']: row['stat_value'] for _, row in df.iterrows()}
            return stats
        except:
            return {}

    @staticmethod
    def _american_to_probability(american_odds: int) -> float:
        """Convert American odds to implied probability"""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)

    @staticmethod
    def _american_to_decimal(american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
