"""
Backtest Framework - Find the Best Value Scoring Approach
=========================================================
Walk-forward validation on 2020-2026 tournaments.
For each test year, trains on ALL prior years only (no data leakage).

Tests 6 approaches:
  1. Current system    - Ridge (45%) + tiered form (20%) + tiered history (5%) + OWGR-proxy (30%)
  2. Ridge-only        - single Ridge model, predicted finish used directly
  3. GBM-only          - Gradient Boosting, predicted finish used directly
  4. Ridge+ESPN        - Ridge with ESPN stats when available
  5. GBM+ESPN          - GBM with ESPN stats when available
  6. Optimized weights - grid-search best blend of model pred + raw features

Metrics per tournament:
  - Spearman rank correlation (does model order players correctly?)
  - Top-10 overlap (how many of model's top 10 were actual top 10?)
  - Top-5 hit rate (was actual winner in model's top 5?)
  - MAE (mean absolute error in finish position)
"""

import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

DB_PATH = "data/cache/pga_data.db"

ESPN_STATS = [
    'scoringAverage', 'greensInRegPct', 'birdiesPerRound',
    'puttsGirAvg', 'savePct', 'driveAccuracyPct', 'yardsPerDrive',
]

BASE_FEATURES = [
    'prior_avg_finish', 'prior_wins', 'prior_top10s', 'prior_events',
    'prior_cut_rate', 'prior_top10_rate', 'prior_best_finish',
    'recent_avg_finish', 'recent_events', 'recent_cut_rate', 'recent_top10_rate',
]

ENHANCED_FEATURES = BASE_FEATURES + [f'espn_{s}' for s in ESPN_STATS]


# ────────────────────────────────────────────
#  DATA LOADING (same logic as training script)
# ────────────────────────────────────────────

def parse_position(pos_str):
    if pd.isna(pos_str):
        return None
    pos_str = str(pos_str).strip().replace('T', '').replace('-', '')
    if pos_str in ('', 'WD', 'DQ', 'CUT', 'MDF', 'W/D'):
        return None
    try:
        val = int(pos_str)
        return val if 1 <= val <= 200 else None
    except ValueError:
        return None


def build_full_dataset():
    """Build the full dataset with features for all player-tournament-year rows"""
    conn = sqlite3.connect(DB_PATH)

    # Load tournament results
    results = pd.read_sql("""
        SELECT player_name, tournament_name, year, position
        FROM tournament_results
        WHERE position IS NOT NULL AND position != 'None'
    """, conn)
    results['pos_numeric'] = results['position'].apply(parse_position)
    print(f"Loaded {len(results)} tournament results")

    # Load ESPN stats
    stats_list = ','.join([f"'{s}'" for s in ESPN_STATS])
    espn_raw = pd.read_sql(f"""
        SELECT player_name, year, stat_name, stat_value
        FROM player_season_stats
        WHERE stat_name IN ({stats_list})
        AND stat_value IS NOT NULL
    """, conn)
    conn.close()

    if not espn_raw.empty:
        espn_pivot = espn_raw.pivot_table(
            index=['player_name', 'year'], columns='stat_name',
            values='stat_value', aggfunc='first'
        ).reset_index()
        espn_pivot = espn_pivot.rename(columns={s: f'espn_{s}' for s in ESPN_STATS})
        # Shift year: use Y-1 stats for year Y predictions
        espn_pivot['year'] = espn_pivot['year'] + 1
    else:
        espn_pivot = pd.DataFrame()

    # ── Compute course-specific priors ──
    print("Computing course priors...")
    results_sorted = results.sort_values(['player_name', 'tournament_name', 'year'])
    prior_rows = []

    for (player, tourn), group in results_sorted.groupby(['player_name', 'tournament_name']):
        group = group.sort_values('year')
        years = group['year'].values
        positions = group['pos_numeric'].values

        for i in range(len(group)):
            yr = years[i]
            target = positions[i]
            if target is None:
                continue  # Skip rows where we can't measure outcome

            prior_pos = positions[:i]  # Only earlier rows in this group
            prior_valid = [p for p in prior_pos if p is not None]

            row = {
                'player_name': player,
                'tournament_name': tourn,
                'year': yr,
                'target_finish': target,
                'prior_events': len(prior_pos),
            }

            if prior_valid:
                row['prior_avg_finish'] = np.mean(prior_valid)
                row['prior_wins'] = sum(1 for p in prior_valid if p == 1)
                row['prior_top10s'] = sum(1 for p in prior_valid if p <= 10)
                row['prior_cut_rate'] = len(prior_valid) / len(prior_pos)
                row['prior_top10_rate'] = row['prior_top10s'] / len(prior_pos)
                row['prior_best_finish'] = min(prior_valid)
            else:
                row['prior_avg_finish'] = None
                row['prior_wins'] = 0
                row['prior_top10s'] = 0
                row['prior_cut_rate'] = None
                row['prior_top10_rate'] = 0.0
                row['prior_best_finish'] = None

            prior_rows.append(row)

    prior_df = pd.DataFrame(prior_rows)
    print(f"  {len(prior_df)} rows with valid targets")

    # ── Compute recent form (Y-2 to Y-1) ──
    print("Computing recent form...")
    recent_rows = []
    for player, pdf in results.groupby('player_name'):
        for yr in pdf['year'].unique():
            mask = (pdf['year'] >= yr - 2) & (pdf['year'] < yr)
            recent = pdf[mask]
            if recent.empty:
                recent_rows.append({
                    'player_name': player, 'year': yr,
                    'recent_avg_finish': None, 'recent_events': 0,
                    'recent_cut_rate': None, 'recent_top10_rate': 0.0,
                })
                continue
            valid = [p for p in recent['pos_numeric'] if p is not None]
            total = len(recent)
            recent_rows.append({
                'player_name': player, 'year': yr,
                'recent_avg_finish': np.mean(valid) if valid else None,
                'recent_events': total,
                'recent_cut_rate': len(valid) / total if total else None,
                'recent_top10_rate': sum(1 for p in valid if p <= 10) / total if total else 0.0,
            })
    recent_df = pd.DataFrame(recent_rows)

    # ── Merge everything ──
    merged = prior_df.merge(recent_df, on=['player_name', 'year'], how='left')
    if not espn_pivot.empty:
        merged = merged.merge(espn_pivot, on=['player_name', 'year'], how='left')

    print(f"Final dataset: {len(merged)} rows")
    return merged


# ────────────────────────────────────────────
#  CURRENT SYSTEM SIMULATION
# ────────────────────────────────────────────

def tiered_form_score(recent_avg, recent_top10_rate):
    """Replicate the tiered form scoring from value_calculator.py"""
    if pd.notna(recent_avg) and recent_avg < 999:
        if recent_avg <= 15:
            score = 35
        elif recent_avg <= 25:
            score = 25
        elif recent_avg <= 35:
            score = 15
        else:
            score = 10
        score += min(recent_top10_rate * 30, 15)
    else:
        score = 10
    return score


def tiered_history_score(prior_avg, prior_wins, prior_top10_rate):
    """Replicate the tiered history scoring from value_calculator.py"""
    if pd.notna(prior_avg):
        if prior_avg <= 10:
            score = 30
        elif prior_avg <= 20:
            score = 25
        elif prior_avg <= 30:
            score = 20
        else:
            score = 10
        if prior_wins > 0:
            score += min(prior_wins * 10, 15)
        score += min(prior_top10_rate * 15, 10)
    else:
        score = 5
    return score


def tiered_owgr_proxy_score(recent_top10_rate, recent_events):
    """
    Simulate OWGR-like scoring using recent_top10_rate as proxy.
    Since we don't have historical OWGR, approximate it.
    Top 10 rate > 0.30 ~ top 10 OWGR, 0.20-0.30 ~ top 50, etc.
    """
    if recent_events == 0:
        return 5
    if recent_top10_rate >= 0.30:
        return 30  # Elite
    elif recent_top10_rate >= 0.20:
        return 25  # Top 50
    elif recent_top10_rate >= 0.12:
        return 20  # Top 100
    elif recent_top10_rate >= 0.05:
        return 15  # Top 200
    else:
        return max(0, 5)


def simulate_current_system(ridge_pred_score, form_score, history_score, owgr_proxy):
    """
    Replicate: course_fit*0.45 + owgr*0.30 + form*0.20 + history*0.05
    ridge_pred_score is on 0-100 scale (100 - predicted_finish * 2)
    """
    return ridge_pred_score * 0.45 + owgr_proxy * 0.30 + form_score * 0.20 + history_score * 0.05


# ────────────────────────────────────────────
#  EVALUATION METRICS
# ────────────────────────────────────────────

def evaluate_per_tournament(predictions_df):
    """
    Compute metrics per tournament, then average.
    predictions_df must have: tournament_key, predicted, actual
    """
    tournament_metrics = []

    for key, group in predictions_df.groupby('tournament_key'):
        if len(group) < 10:
            continue  # Skip tiny tournaments

        actual = group['actual'].values
        predicted = group['predicted'].values

        # Spearman rank correlation (lower predicted = better player)
        corr, _ = spearmanr(predicted, actual)

        # MAE
        mae = mean_absolute_error(actual, predicted)

        # Top-10 overlap: of model's predicted top 10, how many were actual top 10?
        n = min(10, len(group))
        pred_top10_idx = np.argsort(predicted)[:n]  # lowest predicted = best
        actual_top10_idx = np.argsort(actual)[:n]
        overlap = len(set(pred_top10_idx) & set(actual_top10_idx))
        top10_overlap = overlap / n

        # Was the actual winner in model's top 5?
        actual_winner_idx = np.argmin(actual)
        pred_top5_idx = set(np.argsort(predicted)[:5])
        winner_in_top5 = 1 if actual_winner_idx in pred_top5_idx else 0

        # Was actual winner in model's top 10?
        pred_top10_set = set(np.argsort(predicted)[:n])
        winner_in_top10 = 1 if actual_winner_idx in pred_top10_set else 0

        tournament_metrics.append({
            'tournament_key': key,
            'n_players': len(group),
            'spearman': corr,
            'mae': mae,
            'top10_overlap': top10_overlap,
            'winner_in_top5': winner_in_top5,
            'winner_in_top10': winner_in_top10,
        })

    if not tournament_metrics:
        return None

    mdf = pd.DataFrame(tournament_metrics)
    return {
        'n_tournaments': len(mdf),
        'n_predictions': int(mdf['n_players'].sum()),
        'spearman_mean': mdf['spearman'].mean(),
        'spearman_median': mdf['spearman'].median(),
        'mae_mean': mdf['mae'].mean(),
        'top10_overlap_mean': mdf['top10_overlap'].mean(),
        'winner_in_top5_pct': mdf['winner_in_top5'].mean() * 100,
        'winner_in_top10_pct': mdf['winner_in_top10'].mean() * 100,
    }


# ────────────────────────────────────────────
#  WALK-FORWARD BACKTEST
# ────────────────────────────────────────────

def prepare_features(df, feature_cols, means_for_fill=None):
    """Fill NaN and return clean feature matrix"""
    X = df[feature_cols].copy()
    for col in feature_cols:
        if X[col].isna().any():
            fill_val = means_for_fill[col] if means_for_fill and col in means_for_fill else X[col].median()
            if pd.isna(fill_val):
                fill_val = 0
            X[col] = X[col].fillna(fill_val)
    return X


def run_backtest(data, test_years=None):
    """
    Walk-forward backtest. For each test_year, train on all prior years.
    Returns dict of {model_name: metrics_dict}
    """
    if test_years is None:
        test_years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

    # Drop rows with NaN targets and keep only those with course history
    data = data.dropna(subset=['target_finish'])
    has_history = data[data['prior_events'] > 0].copy()
    print(f"\nRows with course history: {len(has_history)}")

    # Also prepare dataset including players WITHOUT history (for models that handle them)
    all_data = data.copy()

    # Identify which rows have full ESPN data
    espn_cols = [f'espn_{s}' for s in ESPN_STATS]
    has_espn_mask = has_history[espn_cols].notna().all(axis=1) if espn_cols[0] in has_history.columns else pd.Series(False, index=has_history.index)

    # Accumulators for each model
    model_predictions = {
        'current_system': [],
        'ridge_only': [],
        'gbm_only': [],
        'ridge_espn': [],
        'gbm_espn': [],
    }

    for test_year in test_years:
        train_mask = has_history['year'] < test_year
        test_mask = has_history['year'] == test_year

        train_df = has_history[train_mask]
        test_df = has_history[test_mask]

        if len(train_df) < 200 or len(test_df) < 50:
            print(f"  Year {test_year}: skipping (train={len(train_df)}, test={len(test_df)})")
            continue

        print(f"\n  Year {test_year}: train={len(train_df)}, test={len(test_df)}, "
              f"tournaments={test_df[['tournament_name']].drop_duplicates().shape[0]}")

        # ── Prepare base features ──
        X_train = prepare_features(train_df, BASE_FEATURES)
        y_train = train_df['target_finish'].values
        X_test = prepare_features(test_df, BASE_FEATURES)
        y_test = test_df['target_finish'].values
        tournament_keys = test_df['tournament_name'].values + '_' + test_df['year'].astype(str).values

        # ── Model 1: Ridge-only ──
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        ridge = Ridge(alpha=100.0)
        ridge.fit(X_train_s, y_train)
        ridge_preds = ridge.predict(X_test_s)

        model_predictions['ridge_only'].append(pd.DataFrame({
            'tournament_key': tournament_keys,
            'predicted': ridge_preds,
            'actual': y_test,
        }))

        # ── Model 2: GBM-only ──
        gbm = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=20, random_state=42,
        )
        gbm.fit(X_train, y_train)  # GBM doesn't need scaling
        gbm_preds = gbm.predict(X_test)

        model_predictions['gbm_only'].append(pd.DataFrame({
            'tournament_key': tournament_keys,
            'predicted': gbm_preds,
            'actual': y_test,
        }))

        # ── Model 3: Current system simulation ──
        ridge_scores = np.clip(100 - ridge_preds * 2, 0, 100)
        form_scores = test_df.apply(
            lambda r: tiered_form_score(r.get('recent_avg_finish'), r.get('recent_top10_rate', 0)), axis=1
        ).values
        history_scores = test_df.apply(
            lambda r: tiered_history_score(r.get('prior_avg_finish'), r.get('prior_wins', 0), r.get('prior_top10_rate', 0)), axis=1
        ).values
        owgr_proxy_scores = test_df.apply(
            lambda r: tiered_owgr_proxy_score(r.get('recent_top10_rate', 0), r.get('recent_events', 0)), axis=1
        ).values

        current_system_scores = (
            ridge_scores * 0.45 +
            owgr_proxy_scores * 0.30 +
            form_scores * 0.20 +
            history_scores * 0.05
        )
        # Invert: higher score = better player, but we compare to actual finish (lower = better)
        # So use negative score as "predicted finish rank"
        model_predictions['current_system'].append(pd.DataFrame({
            'tournament_key': tournament_keys,
            'predicted': -current_system_scores,  # Negate so lower = better
            'actual': y_test,
        }))

        # ── Models 4 & 5: Ridge+ESPN and GBM+ESPN ──
        train_espn_mask = has_espn_mask[train_mask]
        test_espn_mask = has_espn_mask[test_mask]

        train_espn = train_df[train_espn_mask]
        test_espn = test_df[test_espn_mask]

        if len(train_espn) >= 100 and len(test_espn) >= 20:
            X_train_e = prepare_features(train_espn, ENHANCED_FEATURES)
            y_train_e = train_espn['target_finish'].values
            X_test_e = prepare_features(test_espn, ENHANCED_FEATURES)
            y_test_e = test_espn['target_finish'].values
            tkeys_e = test_espn['tournament_name'].values + '_' + test_espn['year'].astype(str).values

            scaler_e = StandardScaler()
            X_train_es = scaler_e.fit_transform(X_train_e)
            X_test_es = scaler_e.transform(X_test_e)

            ridge_e = Ridge(alpha=1.0)
            ridge_e.fit(X_train_es, y_train_e)
            ridge_e_preds = ridge_e.predict(X_test_es)

            model_predictions['ridge_espn'].append(pd.DataFrame({
                'tournament_key': tkeys_e,
                'predicted': ridge_e_preds,
                'actual': y_test_e,
            }))

            gbm_e = GradientBoostingRegressor(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                subsample=0.8, min_samples_leaf=10, random_state=42,
            )
            gbm_e.fit(X_train_e, y_train_e)
            gbm_e_preds = gbm_e.predict(X_test_e)

            model_predictions['gbm_espn'].append(pd.DataFrame({
                'tournament_key': tkeys_e,
                'predicted': gbm_e_preds,
                'actual': y_test_e,
            }))

    # ── Evaluate all models ──
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    results = {}
    for name, pred_list in model_predictions.items():
        if not pred_list:
            print(f"\n  {name}: No predictions (insufficient data)")
            continue
        all_preds = pd.concat(pred_list, ignore_index=True)
        metrics = evaluate_per_tournament(all_preds)
        if metrics:
            results[name] = metrics

    return results


# ────────────────────────────────────────────
#  WEIGHT OPTIMIZATION
# ────────────────────────────────────────────

def optimize_weights(data, test_years=None):
    """
    Grid search over weight combinations for the multi-component approach.
    Tests: (ridge_weight, owgr_proxy_weight, form_weight, history_weight)
    """
    if test_years is None:
        test_years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

    data = data.dropna(subset=['target_finish'])
    has_history = data[data['prior_events'] > 0].copy()

    # Collect all test data with component scores
    all_components = []

    for test_year in test_years:
        train_df = has_history[has_history['year'] < test_year]
        test_df = has_history[has_history['year'] == test_year]

        if len(train_df) < 200 or len(test_df) < 50:
            continue

        X_train = prepare_features(train_df, BASE_FEATURES)
        y_train = train_df['target_finish'].values
        X_test = prepare_features(test_df, BASE_FEATURES)
        y_test = test_df['target_finish'].values

        scaler = StandardScaler()
        ridge = Ridge(alpha=100.0)
        ridge.fit(scaler.fit_transform(X_train), y_train)
        ridge_preds = ridge.predict(scaler.transform(X_test))
        ridge_scores = np.clip(100 - ridge_preds * 2, 0, 100)

        form_scores = test_df.apply(
            lambda r: tiered_form_score(r.get('recent_avg_finish'), r.get('recent_top10_rate', 0)), axis=1
        ).values
        history_scores = test_df.apply(
            lambda r: tiered_history_score(r.get('prior_avg_finish'), r.get('prior_wins', 0), r.get('prior_top10_rate', 0)), axis=1
        ).values
        owgr_proxy = test_df.apply(
            lambda r: tiered_owgr_proxy_score(r.get('recent_top10_rate', 0), r.get('recent_events', 0)), axis=1
        ).values

        # Also compute continuous versions of form/history
        continuous_form = test_df['recent_avg_finish'].fillna(50).values
        continuous_top10 = test_df['recent_top10_rate'].fillna(0).values
        continuous_history = test_df['prior_avg_finish'].fillna(50).values

        tkeys = test_df['tournament_name'].values + '_' + test_df['year'].astype(str).values

        all_components.append(pd.DataFrame({
            'tournament_key': tkeys,
            'actual': y_test,
            'ridge_score': ridge_scores,
            'ridge_pred': ridge_preds,
            'form_tiered': form_scores,
            'history_tiered': history_scores,
            'owgr_proxy': owgr_proxy,
            'recent_avg_finish': continuous_form,
            'recent_top10_rate': continuous_top10,
            'prior_avg_finish': continuous_history,
        }))

    if not all_components:
        return None

    comp_df = pd.concat(all_components, ignore_index=True)

    print("\n" + "=" * 80)
    print("WEIGHT OPTIMIZATION (grid search)")
    print("=" * 80)

    # ── Test 1: Optimize current-style tiered weights ──
    print("\n--- Tiered scoring weights (current approach style) ---")
    print("  Searching (ridge_w, owgr_w, form_w, history_w) that sum to 1.0...")

    best_spearman = -999
    best_weights_tiered = None
    step = 0.05

    for w_ridge in np.arange(0, 1.01, step):
        for w_owgr in np.arange(0, 1.01 - w_ridge, step):
            for w_form in np.arange(0, 1.01 - w_ridge - w_owgr, step):
                w_hist = round(1.0 - w_ridge - w_owgr - w_form, 2)
                if w_hist < -0.001:
                    continue

                blended = (
                    comp_df['ridge_score'] * w_ridge +
                    comp_df['owgr_proxy'] * w_owgr +
                    comp_df['form_tiered'] * w_form +
                    comp_df['history_tiered'] * w_hist
                )

                # Compute mean Spearman across tournaments (negate because higher score = better player)
                spearman_vals = []
                for _, grp in comp_df.groupby('tournament_key'):
                    if len(grp) < 10:
                        continue
                    corr, _ = spearmanr(-blended.loc[grp.index], grp['actual'])
                    spearman_vals.append(corr)

                if spearman_vals:
                    mean_spearman = np.mean(spearman_vals)
                    if mean_spearman > best_spearman:
                        best_spearman = mean_spearman
                        best_weights_tiered = (w_ridge, w_owgr, w_form, w_hist)

    if best_weights_tiered:
        print(f"  BEST tiered weights: Ridge={best_weights_tiered[0]:.2f}, "
              f"OWGR-proxy={best_weights_tiered[1]:.2f}, "
              f"Form={best_weights_tiered[2]:.2f}, "
              f"History={best_weights_tiered[3]:.2f}")
        print(f"  Spearman: {best_spearman:.4f}")
        print(f"  Current weights:    Ridge=0.45, OWGR-proxy=0.30, Form=0.20, History=0.05")

    # ── Test 2: How much does Ridge-only beat the blend? ──
    print("\n--- Ridge prediction alone (no blending) ---")
    ridge_spearman_vals = []
    for _, grp in comp_df.groupby('tournament_key'):
        if len(grp) < 10:
            continue
        corr, _ = spearmanr(grp['ridge_pred'], grp['actual'])
        ridge_spearman_vals.append(corr)
    if ridge_spearman_vals:
        print(f"  Spearman: {np.mean(ridge_spearman_vals):.4f}")

    # ── Test 3: What if we use continuous features instead of tiered brackets? ──
    print("\n--- Optimizing with CONTINUOUS features (no tiered brackets) ---")
    print("  Blending: Ridge pred + recent_avg_finish + recent_top10_rate + prior_avg_finish")

    best_spearman_cont = -999
    best_weights_cont = None

    for w_ridge in np.arange(0, 1.01, step):
        for w_recent_avg in np.arange(0, 1.01 - w_ridge, step):
            for w_recent_t10 in np.arange(0, 1.01 - w_ridge - w_recent_avg, step):
                w_prior = round(1.0 - w_ridge - w_recent_avg - w_recent_t10, 2)
                if w_prior < -0.001:
                    continue

                # All features: lower = better player, EXCEPT recent_top10_rate (higher = better)
                blended = (
                    comp_df['ridge_pred'] * w_ridge +
                    comp_df['recent_avg_finish'] * w_recent_avg +
                    comp_df['recent_top10_rate'] * (-100) * w_recent_t10 +  # Negate & scale
                    comp_df['prior_avg_finish'] * w_prior
                )

                spearman_vals = []
                for _, grp in comp_df.groupby('tournament_key'):
                    if len(grp) < 10:
                        continue
                    corr, _ = spearmanr(blended.loc[grp.index], grp['actual'])
                    spearman_vals.append(corr)

                if spearman_vals:
                    mean_spearman = np.mean(spearman_vals)
                    if mean_spearman > best_spearman_cont:
                        best_spearman_cont = mean_spearman
                        best_weights_cont = (w_ridge, w_recent_avg, w_recent_t10, w_prior)

    if best_weights_cont:
        print(f"  BEST continuous weights: RidgePred={best_weights_cont[0]:.2f}, "
              f"RecentAvg={best_weights_cont[1]:.2f}, "
              f"RecentT10={best_weights_cont[2]:.2f}, "
              f"PriorAvg={best_weights_cont[3]:.2f}")
        print(f"  Spearman: {best_spearman_cont:.4f}")

    return {
        'best_tiered_weights': best_weights_tiered,
        'best_tiered_spearman': best_spearman,
        'ridge_only_spearman': np.mean(ridge_spearman_vals) if ridge_spearman_vals else None,
        'best_continuous_weights': best_weights_cont,
        'best_continuous_spearman': best_spearman_cont,
    }


# ────────────────────────────────────────────
#  GBM FEATURE IMPORTANCE
# ────────────────────────────────────────────

def analyze_gbm_importance(data):
    """Train a final GBM on all data and show feature importance"""
    data = data.dropna(subset=['target_finish'])
    has_history = data[data['prior_events'] > 0].copy()

    X = prepare_features(has_history, BASE_FEATURES)
    y = has_history['target_finish'].values

    gbm = GradientBoostingRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, min_samples_leaf=20, random_state=42,
    )
    gbm.fit(X, y)

    print("\n" + "=" * 80)
    print("GBM FEATURE IMPORTANCE (trained on all data)")
    print("=" * 80)

    importances = sorted(zip(BASE_FEATURES, gbm.feature_importances_),
                         key=lambda x: x[1], reverse=True)
    for name, imp in importances:
        bar = '#' * int(imp * 200)
        print(f"  {name:25s}: {imp:.4f} {bar}")

    return gbm


# ────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────

def main():
    print("=" * 80)
    print("VALUE MODEL BACKTEST FRAMEWORK")
    print("Walk-forward validation: train on years < T, test on year T")
    print("=" * 80)

    data = build_full_dataset()

    # Run walk-forward backtest
    print("\n" + "=" * 80)
    print("WALK-FORWARD BACKTEST (2020-2026)")
    print("=" * 80)

    results = run_backtest(data)

    # Print comparison table
    print("\n" + "=" * 80)
    print("MODEL COMPARISON TABLE")
    print("=" * 80)

    header = (f"  {'Model':<20s} {'Tourn':>6s} {'Preds':>6s} "
              f"{'Spearman':>9s} {'MAE':>7s} {'Top10':>7s} "
              f"{'Win@5':>7s} {'Win@10':>7s}")
    print(header)
    print("  " + "-" * 75)

    # Sort by Spearman (higher is better)
    sorted_results = sorted(results.items(), key=lambda x: x[1]['spearman_mean'], reverse=True)

    for name, m in sorted_results:
        print(f"  {name:<20s} {m['n_tournaments']:>6d} {m['n_predictions']:>6d} "
              f"{m['spearman_mean']:>9.4f} {m['mae_mean']:>7.1f} "
              f"{m['top10_overlap_mean']*100:>6.1f}% "
              f"{m['winner_in_top5_pct']:>6.1f}% "
              f"{m['winner_in_top10_pct']:>6.1f}%")

    print(f"\n  Spearman = rank correlation (higher = model orders players better)")
    print(f"  MAE      = mean absolute error in predicted finish position")
    print(f"  Top10    = overlap between model's top 10 and actual top 10")
    print(f"  Win@5    = % of tournaments where actual winner was in model's top 5")
    print(f"  Win@10   = % of tournaments where actual winner was in model's top 10")

    # Optimize weights
    weight_results = optimize_weights(data)

    # GBM feature importance
    gbm = analyze_gbm_importance(data)

    # ── RECOMMENDATIONS ──
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if sorted_results:
        best_name = sorted_results[0][0]
        best_spearman = sorted_results[0][1]['spearman_mean']
        print(f"\n  Best model by Spearman correlation: {best_name} ({best_spearman:.4f})")

    if weight_results:
        if weight_results.get('best_tiered_weights'):
            w = weight_results['best_tiered_weights']
            print(f"\n  Optimal tiered weights (current approach style):")
            print(f"    Ridge prediction: {w[0]*100:.0f}%")
            print(f"    OWGR-proxy:       {w[1]*100:.0f}%")
            print(f"    Tiered form:      {w[2]*100:.0f}%")
            print(f"    Tiered history:   {w[3]*100:.0f}%")
            print(f"    vs Current:       45% / 30% / 20% / 5%")

        if weight_results.get('best_continuous_weights'):
            w = weight_results['best_continuous_weights']
            print(f"\n  Optimal continuous weights (no tiered brackets):")
            print(f"    Ridge prediction:     {w[0]*100:.0f}%")
            print(f"    Recent avg finish:    {w[1]*100:.0f}%")
            print(f"    Recent top-10 rate:   {w[2]*100:.0f}%")
            print(f"    Prior avg finish:     {w[3]*100:.0f}%")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == '__main__':
    main()
