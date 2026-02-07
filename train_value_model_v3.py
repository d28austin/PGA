"""
Train Value Model V3 - Two-Tier Ridge Regression
Trains on ALL available tournament data (62,845 rows) + ESPN stats (79,040 rows)

Base model: 11 features using only tournament_results (works for ALL players)
Enhanced model: 18 features adding 7 ESPN stats (works for ~195 players/year with ESPN data)

Outputs hardcoded coefficient dicts to paste into value_calculator.py
"""

import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

DB_PATH = "data/cache/pga_data.db"

# 7 ESPN stats to use as enhanced features
ESPN_STATS = [
    'scoringAverage',
    'greensInRegPct',
    'birdiesPerRound',
    'puttsGirAvg',
    'savePct',
    'driveAccuracyPct',
    'yardsPerDrive',
]

BASE_FEATURES = [
    'prior_avg_finish', 'prior_wins', 'prior_top10s', 'prior_events',
    'prior_cut_rate', 'prior_top10_rate', 'prior_best_finish',
    'recent_avg_finish', 'recent_events', 'recent_cut_rate', 'recent_top10_rate',
]

ENHANCED_FEATURES = BASE_FEATURES + [f'espn_{s}' for s in ESPN_STATS]


def load_tournament_results(conn):
    """Load all tournament results"""
    df = pd.read_sql("""
        SELECT player_name, tournament_name, year, position, total_score, earnings
        FROM tournament_results
        WHERE position IS NOT NULL AND position != 'None'
    """, conn)
    print(f"Loaded {len(df)} tournament results")
    return df


def parse_position(pos_str):
    """Parse position string to numeric, return None for non-finishers"""
    if pd.isna(pos_str):
        return None
    pos_str = str(pos_str).strip()
    # Remove T prefix for tied positions
    pos_str = pos_str.replace('T', '').replace('-', '')
    if pos_str in ('', 'WD', 'DQ', 'CUT', 'MDF', 'W/D'):
        return None
    try:
        val = int(pos_str)
        if val < 1 or val > 200:
            return None
        return val
    except ValueError:
        return None


def compute_course_priors(df):
    """
    For each player-tournament-year row, compute stats from EARLIER years only.
    Returns DataFrame with prior features merged in.
    """
    # Parse positions
    df = df.copy()
    df['pos_numeric'] = df['position'].apply(parse_position)

    # Sort by year for proper temporal ordering
    df = df.sort_values(['player_name', 'tournament_name', 'year'])

    # For each row, compute priors from same player + same tournament in earlier years
    prior_rows = []

    # Group by player + tournament
    for (player, tournament), group in df.groupby(['player_name', 'tournament_name']):
        group = group.sort_values('year')
        years = group['year'].values
        positions = group['pos_numeric'].values

        for i in range(len(group)):
            current_year = years[i]
            # Get all prior positions (earlier years only - no data leakage)
            prior_mask = (years < current_year)
            prior_positions = positions[prior_mask]
            # Filter out None
            prior_valid = [p for p in prior_positions if p is not None]

            row = {
                'player_name': player,
                'tournament_name': tournament,
                'year': current_year,
            }

            if len(prior_valid) > 0:
                row['prior_avg_finish'] = np.mean(prior_valid)
                row['prior_wins'] = sum(1 for p in prior_valid if p == 1)
                row['prior_top10s'] = sum(1 for p in prior_valid if p <= 10)
                row['prior_events'] = len(prior_positions)  # Count all attempts including non-finishers
                row['prior_cut_rate'] = len(prior_valid) / len(prior_positions) if len(prior_positions) > 0 else 1.0
                row['prior_top10_rate'] = row['prior_top10s'] / len(prior_positions) if len(prior_positions) > 0 else 0.0
                row['prior_best_finish'] = min(prior_valid)
            else:
                row['prior_avg_finish'] = None
                row['prior_wins'] = 0
                row['prior_top10s'] = 0
                row['prior_events'] = 0
                row['prior_cut_rate'] = None
                row['prior_top10_rate'] = 0.0
                row['prior_best_finish'] = None

            prior_rows.append(row)

    prior_df = pd.DataFrame(prior_rows)
    return prior_df


def compute_recent_form(df):
    """
    For each player-year, compute form from years Y-2 to Y-1 across ALL tournaments.
    """
    df = df.copy()
    df['pos_numeric'] = df['position'].apply(parse_position)

    recent_rows = []

    for player, player_df in df.groupby('player_name'):
        years = sorted(player_df['year'].unique())
        for year in years:
            # Recent = Y-2 to Y-1
            recent_mask = (player_df['year'] >= year - 2) & (player_df['year'] < year)
            recent_data = player_df[recent_mask]

            if len(recent_data) == 0:
                recent_rows.append({
                    'player_name': player,
                    'year': year,
                    'recent_avg_finish': None,
                    'recent_events': 0,
                    'recent_cut_rate': None,
                    'recent_top10_rate': 0.0,
                })
                continue

            positions = recent_data['pos_numeric'].values
            valid_positions = [p for p in positions if p is not None]
            total_events = len(positions)

            recent_rows.append({
                'player_name': player,
                'year': year,
                'recent_avg_finish': np.mean(valid_positions) if valid_positions else None,
                'recent_events': total_events,
                'recent_cut_rate': len(valid_positions) / total_events if total_events > 0 else None,
                'recent_top10_rate': sum(1 for p in valid_positions if p <= 10) / total_events if total_events > 0 else 0.0,
            })

    recent_df = pd.DataFrame(recent_rows)
    return recent_df


def load_espn_stats(conn):
    """Load ESPN season stats, pivoted by stat name"""
    stats_list = ','.join([f"'{s}'" for s in ESPN_STATS])
    df = pd.read_sql(f"""
        SELECT player_name, year, stat_name, stat_value
        FROM player_season_stats
        WHERE stat_name IN ({stats_list})
        AND stat_value IS NOT NULL
    """, conn)

    if df.empty:
        return pd.DataFrame()

    # Pivot to wide format
    pivot = df.pivot_table(
        index=['player_name', 'year'],
        columns='stat_name',
        values='stat_value',
        aggfunc='first'
    ).reset_index()

    # Rename columns with espn_ prefix
    rename_map = {s: f'espn_{s}' for s in ESPN_STATS}
    pivot = pivot.rename(columns=rename_map)

    print(f"Loaded ESPN stats: {len(pivot)} player-years with data")
    return pivot


def build_dataset(conn):
    """Build full training dataset"""
    print("=" * 60)
    print("LOADING DATA")
    print("=" * 60)

    # Load raw data
    results_df = load_tournament_results(conn)

    print("\nComputing course-specific priors (no data leakage)...")
    prior_df = compute_course_priors(results_df)
    print(f"  Generated {len(prior_df)} prior rows")

    print("Computing recent form (Y-2 to Y-1)...")
    recent_df = compute_recent_form(results_df)
    print(f"  Generated {len(recent_df)} recent form rows")

    print("Loading ESPN season stats...")
    espn_df = load_espn_stats(conn)

    # Build target: actual finish position for each player-tournament-year
    results_df['pos_numeric'] = results_df['position'].apply(parse_position)
    target_df = results_df[results_df['pos_numeric'].notna()][
        ['player_name', 'tournament_name', 'year', 'pos_numeric']
    ].copy()
    target_df = target_df.rename(columns={'pos_numeric': 'target_finish'})
    print(f"\nTarget rows (valid finishes): {len(target_df)}")

    # Merge priors
    merged = target_df.merge(
        prior_df,
        on=['player_name', 'tournament_name', 'year'],
        how='inner'
    )
    print(f"After merging priors: {len(merged)} rows")

    # Merge recent form
    merged = merged.merge(
        recent_df,
        on=['player_name', 'year'],
        how='left'
    )
    print(f"After merging recent form: {len(merged)} rows")

    # Merge ESPN stats (from prior year, to avoid data leakage)
    if not espn_df.empty:
        espn_prior = espn_df.copy()
        espn_prior['year'] = espn_prior['year'] + 1  # Shift: use Y-1 stats for year Y
        merged = merged.merge(
            espn_prior,
            on=['player_name', 'year'],
            how='left'
        )
        print(f"After merging ESPN stats: {len(merged)} rows")

    return merged


def train_models(merged):
    """Train base and enhanced Ridge models"""
    print("\n" + "=" * 60)
    print("TRAINING MODELS")
    print("=" * 60)

    # --- BASE MODEL (11 features) ---
    print("\n--- BASE MODEL (11 features) ---")

    # Filter to rows that have prior course history (prior_events > 0)
    base_df = merged[merged['prior_events'] > 0].copy()

    # Fill missing recent form with medians
    for col in ['recent_avg_finish', 'recent_cut_rate']:
        median_val = base_df[col].median()
        base_df[col] = base_df[col].fillna(median_val)

    for col in ['recent_events', 'recent_top10_rate']:
        base_df[col] = base_df[col].fillna(0)

    # Ensure no NaN in base features
    for col in BASE_FEATURES:
        if base_df[col].isna().any():
            median_val = base_df[col].median()
            base_df[col] = base_df[col].fillna(median_val)
            print(f"  Filled {col} NaN with median {median_val:.4f}")

    X_base = base_df[BASE_FEATURES].values
    y_base = base_df['target_finish'].values

    print(f"  Samples: {len(X_base)}")
    print(f"  Features: {len(BASE_FEATURES)}")

    # Standardize
    scaler_base = StandardScaler()
    X_base_scaled = scaler_base.fit_transform(X_base)

    # Cross-validation to find best alpha
    best_alpha = 1.0
    best_cv_score = -999
    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0]:
        model = Ridge(alpha=alpha)
        scores = cross_val_score(model, X_base_scaled, y_base, cv=5, scoring='r2')
        mean_score = scores.mean()
        if mean_score > best_cv_score:
            best_cv_score = mean_score
            best_alpha = alpha

    print(f"  Best alpha: {best_alpha} (CV R²: {best_cv_score:.4f})")

    # Train final base model
    base_model = Ridge(alpha=best_alpha)
    base_model.fit(X_base_scaled, y_base)

    base_r2 = base_model.score(X_base_scaled, y_base)
    print(f"  Training R²: {base_r2:.4f}")

    # --- ENHANCED MODEL (18 features) ---
    print("\n--- ENHANCED MODEL (18 features) ---")

    espn_cols = [f'espn_{s}' for s in ESPN_STATS]
    enhanced_df = merged[merged['prior_events'] > 0].copy()

    # Only keep rows that have all 7 ESPN stats
    espn_mask = enhanced_df[espn_cols].notna().all(axis=1)
    enhanced_df = enhanced_df[espn_mask].copy()

    # Fill missing recent form
    for col in ['recent_avg_finish', 'recent_cut_rate']:
        median_val = enhanced_df[col].median()
        enhanced_df[col] = enhanced_df[col].fillna(median_val)

    for col in ['recent_events', 'recent_top10_rate']:
        enhanced_df[col] = enhanced_df[col].fillna(0)

    # Ensure no NaN
    for col in ENHANCED_FEATURES:
        if enhanced_df[col].isna().any():
            median_val = enhanced_df[col].median()
            enhanced_df[col] = enhanced_df[col].fillna(median_val)
            print(f"  Filled {col} NaN with median {median_val:.4f}")

    X_enhanced = enhanced_df[ENHANCED_FEATURES].values
    y_enhanced = enhanced_df['target_finish'].values

    print(f"  Samples: {len(X_enhanced)}")
    print(f"  Features: {len(ENHANCED_FEATURES)}")

    # Standardize
    scaler_enhanced = StandardScaler()
    X_enhanced_scaled = scaler_enhanced.fit_transform(X_enhanced)

    # Cross-validation
    best_alpha_e = 1.0
    best_cv_score_e = -999
    for alpha in [0.01, 0.1, 1.0, 10.0, 100.0]:
        model = Ridge(alpha=alpha)
        scores = cross_val_score(model, X_enhanced_scaled, y_enhanced, cv=5, scoring='r2')
        mean_score = scores.mean()
        if mean_score > best_cv_score_e:
            best_cv_score_e = mean_score
            best_alpha_e = alpha

    print(f"  Best alpha: {best_alpha_e} (CV R²: {best_cv_score_e:.4f})")

    # Train final enhanced model
    enhanced_model = Ridge(alpha=best_alpha_e)
    enhanced_model.fit(X_enhanced_scaled, y_enhanced)

    enhanced_r2 = enhanced_model.score(X_enhanced_scaled, y_enhanced)
    print(f"  Training R²: {enhanced_r2:.4f}")

    return (base_model, scaler_base, base_df, enhanced_model, scaler_enhanced, enhanced_df)


def print_coefficients(base_model, scaler_base, enhanced_model, scaler_enhanced):
    """Print ready-to-paste Python dicts for value_calculator.py"""
    print("\n" + "=" * 60)
    print("COEFFICIENTS FOR value_calculator.py")
    print("=" * 60)

    # --- BASE MODEL ---
    print("\n# Base model coefficients (11 features)")
    print("self.base_feature_names = [")
    for f in BASE_FEATURES:
        print(f"    '{f}',")
    print("]")

    print(f"\nself.base_intercept = {base_model.intercept_}")

    print("\nself.base_coefficients = {")
    for name, coef in zip(BASE_FEATURES, base_model.coef_):
        print(f"    '{name}': {coef},")
    print("}")

    print("\nself.base_means = {")
    for name, mean in zip(BASE_FEATURES, scaler_base.mean_):
        print(f"    '{name}': {mean},")
    print("}")

    print("\nself.base_stds = {")
    for name, std in zip(BASE_FEATURES, scaler_base.scale_):
        print(f"    '{name}': {std},")
    print("}")

    # --- ENHANCED MODEL ---
    print("\n\n# Enhanced model coefficients (18 features)")
    print("self.enhanced_feature_names = [")
    for f in ENHANCED_FEATURES:
        print(f"    '{f}',")
    print("]")

    print(f"\nself.enhanced_intercept = {enhanced_model.intercept_}")

    print("\nself.enhanced_coefficients = {")
    for name, coef in zip(ENHANCED_FEATURES, enhanced_model.coef_):
        print(f"    '{name}': {coef},")
    print("}")

    print("\nself.enhanced_means = {")
    for name, mean in zip(ENHANCED_FEATURES, scaler_enhanced.mean_):
        print(f"    '{name}': {mean},")
    print("}")

    print("\nself.enhanced_stds = {")
    for name, std in zip(ENHANCED_FEATURES, scaler_enhanced.scale_):
        print(f"    '{name}': {std},")
    print("}")


def print_feature_importance(base_model, scaler_base, enhanced_model, scaler_enhanced):
    """Print feature importance (absolute standardized coefficients)"""
    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE (absolute standardized coefficients)")
    print("=" * 60)

    print("\n--- BASE MODEL ---")
    base_importance = sorted(
        zip(BASE_FEATURES, np.abs(base_model.coef_)),
        key=lambda x: x[1], reverse=True
    )
    for name, imp in base_importance:
        bar = '#' * int(imp * 3)
        print(f"  {name:25s}: {imp:8.4f} {bar}")

    print("\n--- ENHANCED MODEL ---")
    enhanced_importance = sorted(
        zip(ENHANCED_FEATURES, np.abs(enhanced_model.coef_)),
        key=lambda x: x[1], reverse=True
    )
    for name, imp in enhanced_importance:
        bar = '#' * int(imp * 3)
        print(f"  {name:25s}: {imp:8.4f} {bar}")


def print_sample_predictions(base_model, scaler_base, base_df, enhanced_model, scaler_enhanced, enhanced_df):
    """Print sample predictions for well-known players"""
    print("\n" + "=" * 60)
    print("SAMPLE PREDICTIONS")
    print("=" * 60)

    known_players = [
        'Scottie Scheffler', 'Xander Schauffele', 'Rory McIlroy',
        'Jon Rahm', 'Collin Morikawa', 'Viktor Hovland',
        'Brooks Koepka', 'Tiger Woods', 'Jordan Spieth'
    ]

    # Base model predictions
    print("\n--- BASE MODEL (most recent row per player) ---")
    for player in known_players:
        player_rows = base_df[base_df['player_name'] == player]
        if player_rows.empty:
            print(f"  {player:25s}: No data")
            continue

        # Use most recent row
        latest = player_rows.sort_values('year', ascending=False).iloc[0]
        X = latest[BASE_FEATURES].values.reshape(1, -1)
        X_scaled = scaler_base.transform(X)
        pred = base_model.predict(X_scaled)[0]
        actual = latest['target_finish']
        print(f"  {player:25s}: Predicted={pred:5.1f}, Actual={actual:5.0f} (year={int(latest['year'])})")

    # Enhanced model predictions
    print("\n--- ENHANCED MODEL (most recent row per player) ---")
    for player in known_players:
        player_rows = enhanced_df[enhanced_df['player_name'] == player]
        if player_rows.empty:
            print(f"  {player:25s}: No data")
            continue

        latest = player_rows.sort_values('year', ascending=False).iloc[0]
        X = latest[ENHANCED_FEATURES].values.reshape(1, -1)
        X_scaled = scaler_enhanced.transform(X)
        pred = enhanced_model.predict(X_scaled)[0]
        actual = latest['target_finish']
        print(f"  {player:25s}: Predicted={pred:5.1f}, Actual={actual:5.0f} (year={int(latest['year'])})")


def main():
    print("=" * 60)
    print("VALUE MODEL V3 - Two-Tier Ridge Regression Training")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # Build dataset
    merged = build_dataset(conn)

    # Train models
    (base_model, scaler_base, base_df,
     enhanced_model, scaler_enhanced, enhanced_df) = train_models(merged)

    # Print coefficients for hardcoding
    print_coefficients(base_model, scaler_base, enhanced_model, scaler_enhanced)

    # Print feature importance
    print_feature_importance(base_model, scaler_base, enhanced_model, scaler_enhanced)

    # Print sample predictions
    print_sample_predictions(base_model, scaler_base, base_df, enhanced_model, scaler_enhanced, enhanced_df)

    conn.close()

    print("\n" + "=" * 60)
    print("DONE! Copy the coefficients above into value_calculator.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
