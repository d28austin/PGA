"""
Enhanced Value Model with Full Feature Set
Incorporates ALL available historical data for optimal predictions
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from datetime import datetime


class EnhancedValueModel:
    """Enhanced model using all available historical features"""

    def __init__(self, db_path: str = "data/cache/pga_data.db"):
        self.db_path = db_path
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = []

    def get_enhanced_historical_data(self, tournament_name: str, years: list) -> pd.DataFrame:
        """
        Get comprehensive historical data including:
        - Tournament-specific performance
        - Recent overall form
        - OWGR rankings
        - Scoring statistics
        """
        conn = sqlite3.connect(self.db_path)

        year_list = ','.join([str(y) for y in years])

        # Main query with all features
        query = f"""
            WITH player_tournament_history AS (
                -- Tournament-specific history (up to tournament year)
                SELECT
                    tr.player_name,
                    tr.year,
                    tr.tournament_name,
                    tr.position,
                    tr.total_score,
                    COUNT(DISTINCT tr2.year) as prior_events,
                    SUM(CASE WHEN CAST(tr2.position AS INTEGER) = 1 THEN 1 ELSE 0 END) as prior_wins,
                    SUM(CASE WHEN CAST(tr2.position AS INTEGER) <= 10 THEN 1 ELSE 0 END) as prior_top10s,
                    SUM(CASE WHEN tr2.position NOT LIKE '%CUT%' THEN 1 ELSE 0 END) as prior_made_cuts,
                    AVG(CASE
                        WHEN tr2.position NOT LIKE '%WD%'
                        AND tr2.position NOT LIKE '%DQ%'
                        AND tr2.position NOT LIKE '%CUT%'
                        THEN CAST(tr2.position AS INTEGER)
                    END) as prior_avg_finish,
                    MIN(CASE
                        WHEN tr2.position NOT LIKE '%WD%'
                        AND tr2.position NOT LIKE '%DQ%'
                        AND tr2.position NOT LIKE '%CUT%'
                        THEN CAST(tr2.position AS INTEGER)
                    END) as prior_best_finish
                FROM tournament_results tr
                LEFT JOIN tournament_results tr2
                    ON tr2.player_name = tr.player_name
                    AND tr2.tournament_name = tr.tournament_name
                    AND tr2.year < tr.year
                WHERE tr.tournament_name = ?
                AND tr.year IN ({year_list})
                AND tr.position IS NOT NULL
                AND tr.position NOT LIKE '%WD%'
                AND tr.position NOT LIKE '%DQ%'
                GROUP BY tr.player_name, tr.year, tr.position
            ),
            recent_form AS (
                -- Recent form (all tournaments in prior 2 years)
                SELECT
                    pth.player_name,
                    pth.year,
                    COUNT(DISTINCT tr3.tournament_id) as recent_events,
                    SUM(CASE WHEN tr3.position NOT LIKE '%CUT%' THEN 1 ELSE 0 END) as recent_made_cuts,
                    SUM(CASE WHEN CAST(tr3.position AS INTEGER) <= 10 THEN 1 ELSE 0 END) as recent_top10s,
                    AVG(CASE
                        WHEN tr3.position NOT LIKE '%WD%'
                        AND tr3.position NOT LIKE '%DQ%'
                        AND tr3.position NOT LIKE '%CUT%'
                        THEN CAST(tr3.position AS INTEGER)
                    END) as recent_avg_finish
                FROM player_tournament_history pth
                LEFT JOIN tournament_results tr3
                    ON tr3.player_name = pth.player_name
                    AND tr3.year >= pth.year - 2
                    AND tr3.year < pth.year
                WHERE tr3.position IS NOT NULL
                GROUP BY pth.player_name, pth.year
            ),
            owgr_data AS (
                -- OWGR at time of tournament (approximate by year)
                SELECT DISTINCT
                    player_name,
                    MIN(ranking) as best_owgr
                FROM owgr_rankings
                GROUP BY player_name
            )
            SELECT
                pth.*,
                rf.recent_events,
                rf.recent_made_cuts,
                rf.recent_top10s,
                rf.recent_avg_finish,
                COALESCE(rf.recent_made_cuts * 1.0 / NULLIF(rf.recent_events, 0), 0) as recent_cut_rate,
                COALESCE(owgr.best_owgr, 999) as owgr_ranking
            FROM player_tournament_history pth
            LEFT JOIN recent_form rf ON rf.player_name = pth.player_name AND rf.year = pth.year
            LEFT JOIN owgr_data owgr ON owgr.player_name = pth.player_name
        """

        df = pd.read_sql(query, conn, params=(tournament_name,))
        conn.close()

        # Convert position to numeric for target variable
        df['finish_position'] = pd.to_numeric(
            df['position'].str.extract('(\\d+)')[0],
            errors='coerce'
        )

        # Calculate derived features
        df['prior_cut_rate'] = df.apply(
            lambda x: x['prior_made_cuts'] / x['prior_events'] if x['prior_events'] > 0 else 0,
            axis=1
        )

        df['prior_top10_rate'] = df.apply(
            lambda x: x['prior_top10s'] / x['prior_events'] if x['prior_events'] > 0 else 0,
            axis=1
        )

        df['recent_top10_rate'] = df.apply(
            lambda x: x['recent_top10s'] / x['recent_events'] if x.get('recent_events', 0) > 0 else 0,
            axis=1
        )

        return df

    def train_enhanced_model(self, tournament_name: str, years: list):
        """
        Train model using all available features
        """
        print(f"\n{'='*60}")
        print(f"ENHANCED MODEL TRAINING: {tournament_name}")
        print(f"Years: {years}")
        print(f"{'='*60}\n")

        # Get comprehensive data
        df = self.get_enhanced_historical_data(tournament_name, years)

        if df.empty:
            print("No data found")
            return None

        # Only players with tournament history
        df = df[df['prior_events'] > 0]

        print(f"Training samples: {len(df)}")

        # Define feature set
        feature_cols = [
            # Tournament-specific (most important)
            'prior_avg_finish',      # Dominant predictor (66.3%)
            'prior_wins',
            'prior_top10s',
            'prior_events',
            'prior_cut_rate',
            'prior_top10_rate',
            'prior_best_finish',

            # Recent form
            'recent_avg_finish',
            'recent_events',
            'recent_cut_rate',
            'recent_top10_rate',

            # Overall quality
            'owgr_ranking'
        ]

        # Build feature matrix
        X = df[feature_cols].copy()

        # Fill missing values
        X['prior_best_finish'] = X['prior_best_finish'].fillna(999)
        X['recent_avg_finish'] = X['recent_avg_finish'].fillna(50)
        X['recent_events'] = X['recent_events'].fillna(0)
        X['recent_cut_rate'] = X['recent_cut_rate'].fillna(0)
        X['recent_top10_rate'] = X['recent_top10_rate'].fillna(0)
        X['owgr_ranking'] = X['owgr_ranking'].fillna(999)

        y = df['finish_position'].values

        # Remove NaN targets
        mask = ~np.isnan(y)
        X = X[mask]
        y = y[mask]

        print(f"Valid training samples: {len(y)}")

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # Train Ridge Regression
        print(f"\nTraining Ridge Regression...")
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)
        self.feature_names = feature_cols

        # Performance metrics
        r2 = self.model.score(X_scaled, y)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5, scoring='r2')

        print(f"  R² score: {r2:.3f}")
        print(f"  Cross-validation R²: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

        # Feature importance (absolute coefficient values)
        print(f"\n{'='*60}")
        print("FEATURE COEFFICIENTS")
        print(f"{'='*60}")
        coef_df = pd.DataFrame({
            'feature': feature_cols,
            'coefficient': self.model.coef_,
            'abs_coef': np.abs(self.model.coef_)
        }).sort_values('abs_coef', ascending=False)

        print(coef_df.to_string(index=False))

        # Compare with Random Forest
        print(f"\n{'='*60}")
        print("RANDOM FOREST COMPARISON")
        print(f"{'='*60}")
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        rf_r2 = rf.score(X, y)

        print(f"  R² score: {rf_r2:.3f}")
        print(f"\nFeature Importances:")
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        print(importance_df.to_string(index=False))

        # Test predictions
        df_test = df[mask].copy()
        df_test['predicted_finish'] = self.model.predict(X_scaled)

        correlation = np.corrcoef(df_test['finish_position'], df_test['predicted_finish'])[0, 1]
        print(f"\nPrediction correlation: {correlation:.3f}")

        # Save model coefficients to use in app
        self.save_model_config()

        return df_test

    def save_model_config(self):
        """Save model configuration for use in production"""
        config = {
            'feature_names': self.feature_names,
            'coefficients': self.model.coef_.tolist(),
            'intercept': float(self.model.intercept_),
            'scaler_mean': self.scaler.mean_.tolist(),
            'scaler_scale': self.scaler.scale_.tolist()
        }

        import json
        with open('model_config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"\n{'='*60}")
        print("Model config saved to: model_config.json")
        print(f"{'='*60}")


def main():
    """Train enhanced model"""
    print("\n" + "="*60)
    print("ENHANCED VALUE MODEL TRAINING")
    print("="*60)
    print("\nUsing ALL available historical features:")
    print("- Tournament-specific performance (wins, avg finish, etc.)")
    print("- Recent overall form (last 2 years all tournaments)")
    print("- OWGR rankings")
    print("- Cut rates and consistency metrics")
    print()

    model = EnhancedValueModel()

    # Train on WM Phoenix Open
    tournament = "WM Phoenix Open"
    years = [2020, 2021, 2022, 2023, 2024]

    df_results = model.train_enhanced_model(tournament, years)

    if df_results is not None:
        # Save detailed results
        output_file = f"enhanced_model_results_{tournament.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        df_results.to_csv(output_file, index=False)
        print(f"\nDetailed results saved to: {output_file}")

    print("\n" + "="*60)
    print("Training complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
