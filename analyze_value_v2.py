"""
Advanced analysis of Value calculation
"""

import pandas as pd
import numpy as np

# Data from the screenshot
data = [
    {'player': 'Brian Harman', 'no': 10, 'cashes': 8, 'cash_pct': 0.80, 'top10s': 2, 'earnings': 304384, 'owgr': 2.47, 'value': 6.32},
    {'player': 'Cam Davis', 'no': 10, 'cashes': 8, 'cash_pct': 0.80, 'top10s': 2, 'earnings': 279691, 'owgr': 2.42, 'value': 7.01},
    {'player': 'Michael Brennan', 'no': 10, 'cashes': 5, 'cash_pct': 0.50, 'top10s': 1, 'earnings': 238480, 'owgr': 2.28, 'value': 10.46},
    {'player': 'Sam Stevens', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 3, 'earnings': 196783, 'owgr': 2.01, 'value': 6.81},
    {'player': 'Kevin Streelman', 'no': 10, 'cashes': 5, 'cash_pct': 0.50, 'top10s': 1, 'earnings': 184619, 'owgr': 2.06, 'value': 4.37},
    {'player': 'J.T. Poston', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 1, 'earnings': 190198, 'owgr': 1.98, 'value': 4.56},
]

df = pd.DataFrame(data)

print("=" * 100)
print("ADVANCED VALUE ANALYSIS")
print("=" * 100)

# Create a performance score
df['perf_score'] = df['cashes'] + df['top10s'] * 2

# Try weighted combinations
print("\nTesting complex formulas:\n")

# Maybe Value rewards overperformance relative to ranking
# Lower OWGR (better ranking) with high earnings = overperforming = lower value
# Higher OWGR (worse ranking) with high earnings = outperforming expectations = higher value

# Test: (earnings / expected_earnings_for_rank)
# Where expected might be inverse of OWGR
df['test_a'] = (df['earnings'] / 50000) / df['owgr']
print("Test A: (earnings/50000) / owgr")
print(df[['player', 'earnings', 'owgr', 'value', 'test_a']])
print(f"Correlation: {df['value'].corr(df['test_a']):.3f}\n")

# Maybe it's a z-score or percentile based calculation
# Let me try: performance_score / owgr_squared
df['test_b'] = df['perf_score'] / (df['owgr'] ** 2)
print("Test B: (cashes + top10s*2) / (owgr^2)")
print(df[['player', 'perf_score', 'owgr', 'value', 'test_b']])
print(f"Correlation: {df['value'].corr(df['test_b']):.3f}\n")

# Combination of both
df['test_c'] = (df['earnings']/50000 + df['perf_score']) / df['owgr']
print("Test C: (earnings/50000 + perf_score) / owgr")
print(df[['player', 'earnings', 'perf_score', 'owgr', 'value', 'test_c']])
print(f"Correlation: {df['value'].corr(df['test_c']):.3f}\n")

# Maybe it's normalized per player or uses ranking tiers
# Check if Value might be: (performance percentile) / (ranking tier)

print("\n" + "=" * 100)
print("OBSERVATION: Value might be calculated using a proprietary scoring system")
print("=" * 100)
print("\nBest approximation based on data:")
print("Value ≈ (Earnings / $50,000) / OWGR")
print("\nThis captures the concept of 'value' as:")
print("  - Higher earnings relative to world ranking = better value")
print("  - Lower ranked players (higher OWGR number) with good earnings = high value")
print("  - Top ranked players (low OWGR) need exceptional earnings for high value")
