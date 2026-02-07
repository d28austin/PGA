"""
Unified Value Calculator - V4 Backtest-Optimized
Continuous scoring with empirically optimized weights.

Validated by walk-forward backtest across 243 tournaments and 15,559 predictions (2020-2026).
Replaces tiered bracket scoring with continuous linear scaling.
Two-tier Ridge model (base 11 features / enhanced 18 features with ESPN stats).

Key finding: recent form (avg finish + top-10 rate) accounts for ~85% of predictive signal.
Ridge regression adds ~10%. Course history adds ~5%.
"""

import pandas as pd
import numpy as np
import sqlite3
from typing import Optional, Dict


class ValueCalculator:
    """
    Calculates player value using backtest-optimized continuous scoring.

    Walk-forward validation (2020-2026, 243 tournaments) found:
      - With OWGR:    Ridge 10% + RecentAvg 35% + Top10Rate 15% + OWGR 35% + Prior 5%
      - Without OWGR: Ridge 10% + RecentAvg 45% + Top10Rate 40% + Prior 5%

    Ridge prediction uses two-tier model:
      - Base (11 features): works for all players with course history
      - Enhanced (18 features): adds 7 ESPN stats when available
    """

    def __init__(self, db_path: str = "data/cache/pga_data.db"):
        self.db_path = db_path

        # ── Base model coefficients (11 features) ──
        # Trained on 26,198 samples across 552 tournaments (2014-2026)
        # Ridge alpha=100.0, CV R²=0.024, Training R²=0.081
        self.base_feature_names = [
            'prior_avg_finish', 'prior_wins', 'prior_top10s', 'prior_events',
            'prior_cut_rate', 'prior_top10_rate', 'prior_best_finish',
            'recent_avg_finish', 'recent_events', 'recent_cut_rate', 'recent_top10_rate',
        ]

        self.base_intercept = 38.84395755401176

        self.base_coefficients = {
            'prior_avg_finish': 1.6877718635941619,
            'prior_wins': -0.12616353319221302,
            'prior_top10s': -2.0330187756171565,
            'prior_events': 2.088690351961639,
            'prior_cut_rate': 0.0,
            'prior_top10_rate': 0.6436074673825478,
            'prior_best_finish': -0.49134082925763933,
            'recent_avg_finish': 1.372332056073067,
            'recent_events': -2.5040953470201273,
            'recent_cut_rate': 0.0,
            'recent_top10_rate': -4.565260234339589,
        }

        self.base_means = {
            'prior_avg_finish': 33.99204263335972,
            'prior_wins': 0.04775173677379953,
            'prior_top10s': 0.42194060615314144,
            'prior_events': 2.644705702725399,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.14460615535315896,
            'prior_best_finish': 23.333307886098176,
            'recent_avg_finish': 44.28894535027296,
            'recent_events': 35.73982746774563,
            'recent_cut_rate': 1.0,
            'recent_top10_rate': 0.1372488348229849,
        }

        self.base_stds = {
            'prior_avg_finish': 15.68581060548048,
            'prior_wins': 0.22778106082085955,
            'prior_top10s': 0.7877184548644424,
            'prior_events': 1.9347604471018094,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.27214792200924376,
            'prior_best_finish': 19.332452093028806,
            'recent_avg_finish': 6.921851851097687,
            'recent_events': 14.36231181291866,
            'recent_cut_rate': 1.0,
            'recent_top10_rate': 0.12038391548068551,
        }

        # ── Enhanced model coefficients (18 features) ──
        # Trained on 6,446 samples with ESPN stats (2014-2026)
        # Ridge alpha=1.0, Training R²=0.065
        self.enhanced_feature_names = [
            'prior_avg_finish', 'prior_wins', 'prior_top10s', 'prior_events',
            'prior_cut_rate', 'prior_top10_rate', 'prior_best_finish',
            'recent_avg_finish', 'recent_events', 'recent_cut_rate', 'recent_top10_rate',
            'espn_scoringAverage', 'espn_greensInRegPct', 'espn_birdiesPerRound',
            'espn_puttsGirAvg', 'espn_savePct', 'espn_driveAccuracyPct', 'espn_yardsPerDrive',
        ]

        self.enhanced_intercept = 36.00837728824077

        self.enhanced_coefficients = {
            'prior_avg_finish': 0.8260549250078905,
            'prior_wins': -0.4084190875253277,
            'prior_top10s': -2.4821297039222623,
            'prior_events': 1.848019127573872,
            'prior_cut_rate': 0.0,
            'prior_top10_rate': 1.22940458423771,
            'prior_best_finish': 0.44589267157191365,
            'recent_avg_finish': 2.106639587225473,
            'recent_events': -1.6902629244352287,
            'recent_cut_rate': 0.0,
            'recent_top10_rate': -1.4431917804789784,
            'espn_scoringAverage': 32.22531460614977,
            'espn_greensInRegPct': 0.6476008852347399,
            'espn_birdiesPerRound': -2.897769269848875,
            'espn_puttsGirAvg': -7.911281747488561,
            'espn_savePct': -3.010158725777504,
            'espn_driveAccuracyPct': -2.909975791933667,
            'espn_yardsPerDrive': -16.350147621311805,
        }

        self.enhanced_means = {
            'prior_avg_finish': 35.663601800946665,
            'prior_wins': 0.06531182128451753,
            'prior_top10s': 0.5570896680111698,
            'prior_events': 3.2665218740304063,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.15430297716211464,
            'prior_best_finish': 22.339590443686006,
            'recent_avg_finish': 41.99462032806309,
            'recent_events': 38.575085324232084,
            'recent_cut_rate': 1.0,
            'recent_top10_rate': 0.15774130479913107,
            'espn_scoringAverage': 64.96100867049333,
            'espn_greensInRegPct': 62.10648539388769,
            'espn_birdiesPerRound': 3.566948709308098,
            'espn_puttsGirAvg': 1.6259457027614026,
            'espn_savePct': 48.536908858827175,
            'espn_driveAccuracyPct': 56.52070089636984,
            'espn_yardsPerDrive': 278.19657151722,
        }

        self.enhanced_stds = {
            'prior_avg_finish': 16.730051212395736,
            'prior_wins': 0.2733094663895171,
            'prior_top10s': 0.9408912241667015,
            'prior_events': 2.348087444689427,
            'prior_cut_rate': 1.0,
            'prior_top10_rate': 0.2592437934958451,
            'prior_best_finish': 20.551644597054015,
            'recent_avg_finish': 7.405465309246186,
            'recent_events': 11.901727861057172,
            'recent_cut_rate': 1.0,
            'recent_top10_rate': 0.10715724182462034,
            'espn_scoringAverage': 18.309401610772717,
            'espn_greensInRegPct': 17.64877030598196,
            'espn_birdiesPerRound': 1.0416255440022164,
            'espn_puttsGirAvg': 0.4586554191489866,
            'espn_savePct': 14.943022905561879,
            'espn_driveAccuracyPct': 16.553291139025667,
            'espn_yardsPerDrive': 78.74269539400792,
        }

        self._espn_stat_names = [
            'scoringAverage', 'greensInRegPct', 'birdiesPerRound',
            'puttsGirAvg', 'savePct', 'driveAccuracyPct', 'yardsPerDrive',
        ]

    # ── Ridge prediction helpers ──

    def _predict(self, features, feature_names, coefficients, means, stds, intercept):
        """Run Ridge prediction with z-score standardization"""
        predicted = intercept
        for name in feature_names:
            std = stds[name]
            if std == 0 or std == 1.0:
                continue
            z = (features[name] - means[name]) / std
            predicted += coefficients[name] * z
        return predicted

    def _get_espn_stats(self, player_name, year=2025):
        """Get ESPN season stats. Returns dict of espn_* features or None."""
        try:
            conn = sqlite3.connect(self.db_path)
            stats_list = ','.join([f"'{s}'" for s in self._espn_stat_names])
            df = pd.read_sql(f"""
                SELECT stat_name, stat_value
                FROM player_season_stats
                WHERE player_name = ? AND year = ?
                AND stat_name IN ({stats_list}) AND stat_value IS NOT NULL
            """, conn, params=(player_name, year))
            conn.close()

            if len(df) < len(self._espn_stat_names):
                return None

            result = {}
            for _, row in df.iterrows():
                result[f"espn_{row['stat_name']}"] = row['stat_value']

            for stat in self._espn_stat_names:
                if f'espn_{stat}' not in result:
                    return None
            return result
        except Exception:
            return None

    # ── Continuous scoring functions (0-100, higher = better) ──

    @staticmethod
    def _score_avg_finish(avg_finish):
        """Average finish position to 0-100. Lower finish = higher score."""
        if pd.isna(avg_finish) or avg_finish >= 999:
            return None
        # finish=1 → 100, finish=60 → 0
        return max(0.0, min(100.0, (60.0 - avg_finish) / 59.0 * 100.0))

    @staticmethod
    def _score_top10_rate(rate):
        """Top-10 rate to 0-100. Higher rate = higher score."""
        # rate=0.40 → 100, rate=0 → 0
        return max(0.0, min(100.0, rate * 250.0))

    @staticmethod
    def _score_owgr(ranking):
        """OWGR ranking to 0-100. Lower ranking = higher score."""
        if ranking is None or ranking >= 999:
            return None
        # OWGR 1 → 100, OWGR 300 → 0
        return max(0.0, min(100.0, (300.0 - ranking) / 299.0 * 100.0))

    @staticmethod
    def _score_ridge_pred(predicted_finish):
        """Ridge predicted finish to 0-100. Lower prediction = higher score."""
        # pred=1 → 100, pred=55 → 0
        return max(0.0, min(100.0, (55.0 - predicted_finish) / 54.0 * 100.0))

    # ── Main calculation ──

    def calculate_value(
        self,
        player_data: pd.Series,
        tournament_name: Optional[str] = None,
        odds: Optional[float] = None,
        player_name: Optional[str] = None
    ) -> Dict:
        """
        Calculate comprehensive value score for a player.

        Uses backtest-optimized continuous scoring with weights validated
        across 243 tournaments and 15,559 predictions (2020-2026).

        Args:
            player_data: Series with player statistics
            tournament_name: Tournament name (unused, kept for API compat)
            odds: American odds (e.g., +450, -110) if available
            player_name: Player name (enables enhanced model with ESPN stats)

        Returns:
            Dictionary with value metrics and components
        """
        # ── Extract raw features ──
        prior_events = player_data.get('events', 0) or player_data.get('appearances', 0) or 0
        prior_wins = player_data.get('wins', 0) or 0
        prior_top10s = player_data.get('top_10s', 0) or 0
        prior_avg_finish = player_data.get('avg_finish', None)
        prior_best_finish = player_data.get('best_finish', 999)
        prior_made_cuts = player_data.get('made_cuts', prior_events)

        prior_cut_rate = prior_made_cuts / prior_events if prior_events > 0 else 1.0
        prior_top10_rate = prior_top10s / prior_events if prior_events > 0 else 0.0

        recent_avg_finish = player_data.get('recent_avg_finish', None)
        recent_events = player_data.get('recent_events', 0)
        recent_made_cuts = player_data.get('recent_made_cuts', recent_events)
        recent_top10s_count = player_data.get('recent_top10s', 0)

        recent_cut_rate = recent_made_cuts / recent_events if recent_events > 0 else 0.99
        recent_top10_rate = recent_top10s_count / recent_events if recent_events > 0 else 0.0

        owgr_ranking = player_data.get('owgr_numeric', 999) or player_data.get('owgr', 999)

        # ── Compute continuous component scores (0-100) ──

        # Recent form scores
        recent_avg_score = self._score_avg_finish(recent_avg_finish) if recent_events > 0 else None
        top10_rate_score = self._score_top10_rate(recent_top10_rate) if recent_events > 0 else None

        # OWGR score
        owgr_score = self._score_owgr(owgr_ranking)

        # Ridge prediction score (requires course history)
        ridge_score = None
        predicted_finish = None
        if prior_events > 0:
            features = {
                'prior_avg_finish': prior_avg_finish if pd.notna(prior_avg_finish) else self.base_means['prior_avg_finish'],
                'prior_wins': prior_wins,
                'prior_top10s': prior_top10s,
                'prior_events': prior_events,
                'prior_cut_rate': prior_cut_rate,
                'prior_top10_rate': prior_top10_rate,
                'prior_best_finish': prior_best_finish if prior_best_finish < 999 else self.base_means['prior_best_finish'],
                'recent_avg_finish': recent_avg_finish if pd.notna(recent_avg_finish) else self.base_means['recent_avg_finish'],
                'recent_events': recent_events if recent_events > 0 else self.base_means['recent_events'],
                'recent_cut_rate': recent_cut_rate,
                'recent_top10_rate': recent_top10_rate,
            }

            # Try enhanced model if player_name provided
            used_enhanced = False
            if player_name:
                espn_stats = self._get_espn_stats(player_name)
                if espn_stats is not None:
                    enhanced_features = dict(features)
                    # Use enhanced means for fallback values
                    enhanced_features['recent_avg_finish'] = recent_avg_finish if pd.notna(recent_avg_finish) else self.enhanced_means['recent_avg_finish']
                    enhanced_features['recent_events'] = recent_events if recent_events > 0 else self.enhanced_means['recent_events']
                    enhanced_features.update(espn_stats)
                    predicted_finish = self._predict(
                        enhanced_features, self.enhanced_feature_names,
                        self.enhanced_coefficients, self.enhanced_means,
                        self.enhanced_stds, self.enhanced_intercept,
                    )
                    used_enhanced = True

            if not used_enhanced:
                predicted_finish = self._predict(
                    features, self.base_feature_names,
                    self.base_coefficients, self.base_means,
                    self.base_stds, self.base_intercept,
                )

            ridge_score = self._score_ridge_pred(predicted_finish)

        # Course history score
        prior_score = self._score_avg_finish(prior_avg_finish) if prior_events > 0 else None

        # ── Weighted combination (backtest-optimized) ──
        # Weights from walk-forward validation on 243 tournaments (Spearman=0.244):
        #   With OWGR:    Ridge 10% + RecentAvg 35% + Top10Rate 15% + OWGR 35% + Prior 5%
        #   Without OWGR: Ridge 10% + RecentAvg 45% + Top10Rate 40% + Prior 5%
        # Missing components redistribute weight proportionally to remaining components.

        has_owgr = owgr_score is not None

        components = []  # (score, target_weight)

        if ridge_score is not None:
            components.append(('ridge', ridge_score, 0.10))

        if recent_avg_score is not None:
            components.append(('recent_avg', recent_avg_score, 0.35 if has_owgr else 0.45))

        if top10_rate_score is not None:
            components.append(('top10_rate', top10_rate_score, 0.15 if has_owgr else 0.40))

        if has_owgr:
            components.append(('owgr', owgr_score, 0.35))

        if prior_score is not None:
            components.append(('prior', prior_score, 0.05))

        if components:
            total_weight = sum(w for _, _, w in components)
            base_value = sum(s * w for _, s, w in components) / total_weight
        else:
            base_value = 0.0

        # ── Build result dict (backward-compatible keys) ──
        result = {
            'base_value': base_value,
            'course_fit_score': ridge_score if ridge_score is not None else 0,
            'history_score': prior_score if prior_score is not None else 0,
            'form_score': recent_avg_score if recent_avg_score is not None else 0,
            'owgr_score': owgr_score if owgr_score is not None else 0,
            'predicted_finish': predicted_finish,
        }

        # ── Odds-based metrics (if available) ──
        if odds is not None and pd.notna(odds):
            implied_prob = self._american_to_probability(odds)

            # Estimate win probability from value score
            if predicted_finish is not None and pd.notna(prior_avg_finish):
                if predicted_finish <= 5:
                    estimated_win_prob = 0.20
                elif predicted_finish <= 10:
                    estimated_win_prob = 0.10
                elif predicted_finish <= 15:
                    estimated_win_prob = 0.05
                elif predicted_finish <= 25:
                    estimated_win_prob = 0.02
                elif predicted_finish <= 40:
                    estimated_win_prob = 0.01
                else:
                    estimated_win_prob = 0.005

                win_rate = prior_wins / prior_events if prior_events > 0 else 0
                estimated_win_prob = (estimated_win_prob * 0.7) + (win_rate * 0.3)
                estimated_win_prob = max(0.001, min(estimated_win_prob, 0.30))
            else:
                estimated_win_prob = base_value / 2000
                estimated_win_prob = max(0.001, min(estimated_win_prob, 0.05))

            # Value edge
            if implied_prob > 0.001:
                if implied_prob < 0.02:
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
                'final_value_score': final_value,
            })
        else:
            result['final_value_score'] = base_value

        return result

    def get_player_season_stats(self, player_name: str, year: int = 2025) -> Dict:
        """Get ESPN season statistics for a player"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql("""
                SELECT stat_name, stat_value
                FROM player_season_stats
                WHERE player_name = ? AND year = ?
            """, conn, params=(player_name, year))
            conn.close()
            return {row['stat_name']: row['stat_value'] for _, row in df.iterrows()}
        except Exception:
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
