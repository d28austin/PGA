"""
Value Model Backtesting and Optimization

This script:
1. Pulls historical tournament results
2. Calculates value scores using your current model
3. Compares predicted value vs actual finishes
4. Runs regression to find optimal weights
5. Tests different feature combinations
6. Outputs recommendations for model improvements
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from datetime import datetime


class ValueModelAnalyzer:
    """Analyze and optimize the value prediction model"""

    def __init__(self, db_path: str = "data/cache/pga_data.db"):
        self.db_path = db_path

    def get_historical_performance(self, tournament_name: str, years: list) -> pd.DataFrame:
        """
        Get historical tournament results for backtesting

        Args:
            tournament_name: Tournament to analyze
            years: List of years to include

        Returns:
            DataFrame with player performance
        """
        conn = sqlite3.connect(self.db_path)

        year_list = ','.join([str(y) for y in years])

        query = f"""
            SELECT
                tr.player_name,
                tr.year,
                tr.tournament_name,
                tr.position,
                tr.total_score,
                tr.earnings,
                COUNT(DISTINCT tr2.year) as prior_events,
                SUM(CASE WHEN CAST(tr2.position AS INTEGER) = 1 THEN 1 ELSE 0 END) as prior_wins,
                SUM(CASE WHEN CAST(tr2.position AS INTEGER) <= 10 THEN 1 ELSE 0 END) as prior_top10s,
                AVG(CASE
                    WHEN tr2.position NOT LIKE '%WD%'
                    AND tr2.position NOT LIKE '%DQ%'
                    AND tr2.position NOT LIKE '%CUT%'
                    THEN CAST(tr2.position AS INTEGER)
                END) as prior_avg_finish
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
            GROUP BY tr.player_name, tr.year
        """

        df = pd.read_sql(query, conn, params=(tournament_name,))
        conn.close()

        # Convert position to numeric for analysis
        df['finish_position'] = pd.to_numeric(df['position'].str.extract('(\d+)')[0], errors='coerce')

        return df

    def calculate_current_model_score(self, row: pd.Series) -> float:
        """
        Calculate value score using your current model

        Args:
            row: Player data row

        Returns:
            Value score
        """
        history_score = 0

        # Prior wins at tournament
        if row.get('prior_wins', 0) > 0:
            history_score += 30

        # Prior top 10 rate
        if row.get('prior_events', 0) > 0:
            top_10_rate = row.get('prior_top10s', 0) / row['prior_events']
            history_score += min(top_10_rate * 100, 40)

        # Average finish (course fit proxy)
        avg_finish = row.get('prior_avg_finish', 70)
        if pd.notna(avg_finish):
            if avg_finish <= 20:
                history_score += 20
            elif avg_finish <= 30:
                history_score += 10

        return history_score

    def backtest_model(self, tournament_name: str, years: list) -> pd.DataFrame:
        """
        Backtest the value model against actual results

        Args:
            tournament_name: Tournament to test
            years: Years to include

        Returns:
            DataFrame with predictions vs actuals
        """
        print(f"\n{'='*60}")
        print(f"Backtesting: {tournament_name}")
        print(f"Years: {years}")
        print(f"{'='*60}\n")

        # Get historical data
        df = self.get_historical_performance(tournament_name, years)

        if df.empty:
            print("No data found for this tournament")
            return pd.DataFrame()

        # Only include players with prior history (can't predict without data)
        df = df[df['prior_events'] > 0]

        print(f"Players with prior history: {len(df)}")

        # Calculate value score using current model
        df['predicted_value'] = df.apply(self.calculate_current_model_score, axis=1)

        # Analyze results
        print(f"\nValue Score Stats:")
        print(f"  Mean: {df['predicted_value'].mean():.1f}")
        print(f"  Median: {df['predicted_value'].median():.1f}")
        print(f"  Std: {df['predicted_value'].std():.1f}")

        print(f"\nActual Finish Stats:")
        print(f"  Mean: {df['finish_position'].mean():.1f}")
        print(f"  Median: {df['finish_position'].median():.1f}")

        # Calculate correlation
        correlation = df[['predicted_value', 'finish_position']].corr().iloc[0, 1]
        print(f"\nCorrelation (value vs finish): {correlation:.3f}")
        print(f"  (Negative is good - high value = low finish position)")

        return df

    def find_optimal_weights(self, df: pd.DataFrame) -> dict:
        """
        Use regression to find optimal feature weights

        Args:
            df: Backtest results DataFrame

        Returns:
            Dictionary with optimal weights
        """
        print(f"\n{'='*60}")
        print("REGRESSION ANALYSIS")
        print(f"{'='*60}\n")

        # Prepare features
        features = []
        feature_names = []

        # Feature 1: Prior wins
        features.append(df['prior_wins'].fillna(0))
        feature_names.append('prior_wins')

        # Feature 2: Prior top 10s
        features.append(df['prior_top10s'].fillna(0))
        feature_names.append('prior_top10s')

        # Feature 3: Prior events (experience)
        features.append(df['prior_events'].fillna(0))
        feature_names.append('prior_events')

        # Feature 4: Prior avg finish
        features.append(df['prior_avg_finish'].fillna(50))
        feature_names.append('prior_avg_finish')

        # Create feature matrix
        X = np.column_stack(features)
        y = df['finish_position'].values

        # Remove rows with missing target
        mask = ~np.isnan(y)
        X = X[mask]
        y = y[mask]

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Linear Regression
        print("1. Linear Regression")
        lr = LinearRegression()
        lr.fit(X_scaled, y)

        print(f"   R² score: {lr.score(X_scaled, y):.3f}")
        print(f"   Coefficients:")
        for name, coef in zip(feature_names, lr.coef_):
            print(f"     {name:20s}: {coef:8.3f}")

        # Ridge Regression (with regularization)
        print(f"\n2. Ridge Regression (regularized)")
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_scaled, y)

        print(f"   R² score: {ridge.score(X_scaled, y):.3f}")
        print(f"   Coefficients:")
        for name, coef in zip(feature_names, ridge.coef_):
            print(f"     {name:20s}: {coef:8.3f}")

        # Random Forest (non-linear relationships)
        print(f"\n3. Random Forest")
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)

        print(f"   R² score: {rf.score(X, y):.3f}")
        print(f"   Feature Importances:")
        for name, importance in zip(feature_names, rf.feature_importances_):
            print(f"     {name:20s}: {importance:8.3f}")

        # Cross-validation scores
        print(f"\n4. Cross-Validation Scores (5-fold)")
        cv_scores = cross_val_score(ridge, X_scaled, y, cv=5, scoring='r2')
        print(f"   Mean R²: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

        # Return optimal weights from Ridge (most stable)
        optimal_weights = {
            name: float(coef) for name, coef in zip(feature_names, ridge.coef_)
        }

        return optimal_weights

    def analyze_top_predictors(self, df: pd.DataFrame):
        """
        Analyze which features best predict top finishes

        Args:
            df: Backtest results DataFrame
        """
        print(f"\n{'='*60}")
        print("TOP FINISH ANALYSIS")
        print(f"{'='*60}\n")

        # Compare top value scores vs actual top finishers
        top_10_value = df.nlargest(10, 'predicted_value')
        actual_top_10 = df.nsmallest(10, 'finish_position')

        print("Top 10 by Predicted Value:")
        for i, row in top_10_value.iterrows():
            print(f"  {row['player_name']:25s} Value: {row['predicted_value']:5.1f} Actual: {row['finish_position']:3.0f}")

        print(f"\nTop 10 Actual Finishers:")
        for i, row in actual_top_10.iterrows():
            print(f"  {row['player_name']:25s} Value: {row['predicted_value']:5.1f} Actual: {row['finish_position']:3.0f}")

        # Calculate overlap
        predicted_names = set(top_10_value['player_name'])
        actual_names = set(actual_top_10['player_name'])
        overlap = len(predicted_names & actual_names)

        print(f"\nOverlap: {overlap}/10 ({overlap*10}%)")

    def generate_recommendations(self, weights: dict, correlation: float):
        """
        Generate recommendations for model improvement

        Args:
            weights: Optimal feature weights
            correlation: Model correlation with results
        """
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS")
        print(f"{'='*60}\n")

        print(f"Current Model Correlation: {correlation:.3f}")

        if abs(correlation) < 0.3:
            print("\n[!] WEAK CORRELATION")
            print("   Consider adding more features:")
            print("   - Recent form (last 5-10 events)")
            print("   - Strokes gained statistics")
            print("   - Course-specific stats (distance, accuracy)")
            print("   - Current season performance")

        elif abs(correlation) < 0.5:
            print("\n[+] MODERATE CORRELATION")
            print("   Model has predictive power. Improvements:")
            print("   - Fine-tune feature weights")
            print("   - Add statistical features")
            print("   - Consider non-linear relationships")

        else:
            print("\n[++] STRONG CORRELATION")
            print("   Model is working well!")
            print("   - Continue monitoring performance")
            print("   - Test on other tournaments")

        print(f"\nOptimal Feature Weights:")
        print(f"  (Negative weights = lower is better)")
        for feature, weight in weights.items():
            print(f"    {feature:20s}: {weight:8.3f}")


def main():
    """Main analysis function"""
    print("\n" + "="*60)
    print("VALUE MODEL BACKTESTING & OPTIMIZATION")
    print("="*60)
    print("\nThis will analyze your value model against actual results")
    print("and suggest optimal weights for predictions.\n")

    analyzer = ValueModelAnalyzer()

    # Test on a specific tournament
    tournament = "WM Phoenix Open"
    years = [2020, 2021, 2022, 2023, 2024]

    # Backtest
    df = analyzer.backtest_model(tournament, years)

    if not df.empty:
        # Find optimal weights
        weights = analyzer.find_optimal_weights(df)

        # Analyze top predictors
        analyzer.analyze_top_predictors(df)

        # Calculate correlation
        correlation = df[['predicted_value', 'finish_position']].corr().iloc[0, 1]

        # Generate recommendations
        analyzer.generate_recommendations(weights, correlation)

        # Save results
        output_file = f"backtest_results_{tournament.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(output_file, index=False)
        print(f"\n\nResults saved to: {output_file}")

    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
