"""
Analyze the Value calculation from the screenshot
"""

import pandas as pd

# Data from the screenshot
data = [
    {'player': 'Brian Harman', 'no': 10, 'cashes': 8, 'cash_pct': 0.80, 'top10s': 2, 'earnings': 304384, 'owgr': 2.47, 'value': 6.32},
    {'player': 'Cam Davis', 'no': 10, 'cashes': 8, 'cash_pct': 0.80, 'top10s': 2, 'earnings': 279691, 'owgr': 2.42, 'value': 7.01},
    {'player': 'Michael Brennan', 'no': 10, 'cashes': 5, 'cash_pct': 0.50, 'top10s': 1, 'earnings': 238480, 'owgr': 2.28, 'value': 10.46},
    {'player': 'Daniel Berger', 'no': 10, 'cashes': 8, 'cash_pct': 0.80, 'top10s': 0, 'earnings': 245352, 'owgr': 2.61, 'value': None},
    {'player': 'Sam Stevens', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 3, 'earnings': 196783, 'owgr': 2.01, 'value': 6.81},
    {'player': 'Kevin Streelman', 'no': 10, 'cashes': 5, 'cash_pct': 0.50, 'top10s': 1, 'earnings': 184619, 'owgr': 2.06, 'value': 4.37},
    {'player': 'J.T. Poston', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 1, 'earnings': 190198, 'owgr': 1.98, 'value': 4.56},
    {'player': 'Cameron Percy', 'no': 10, 'cashes': 4, 'cash_pct': 0.40, 'top10s': 0, 'earnings': 199764, 'owgr': 16.2, 'value': 6.23},
    {'player': 'Nick Echavarria', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 2, 'earnings': 193358, 'owgr': 1.90, 'value': 4.91},
    {'player': 'Joel Dahmen', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 3, 'earnings': 220440, 'owgr': 1.87, 'value': 5.82},
    {'player': 'Brad Cauley', 'no': 10, 'cashes': 5, 'cash_pct': 0.60, 'top10s': 0, 'earnings': 174201, 'owgr': 18.2, 'value': 4.08},
    {'player': 'Ben Martin', 'no': 10, 'cashes': 7, 'cash_pct': 0.70, 'top10s': 1, 'earnings': 155458, 'owgr': 19.2, 'value': 4.69},
]

df = pd.DataFrame(data)
df = df[df['value'].notna()]  # Remove rows without value

print("=" * 100)
print("ANALYZING VALUE CALCULATION")
print("=" * 100)

# Test various formulas
print("\nTesting different formulas:\n")

# Formula 1: cashes / owgr
df['test1'] = df['cashes'] / df['owgr']
print("Formula 1: cashes / owgr")
print(df[['player', 'cashes', 'owgr', 'value', 'test1']].head(5))
print(f"Correlation: {df['value'].corr(df['test1']):.3f}\n")

# Formula 2: (cashes + top10s) / owgr
df['test2'] = (df['cashes'] + df['top10s']) / df['owgr']
print("Formula 2: (cashes + top10s) / owgr")
print(df[['player', 'cashes', 'top10s', 'owgr', 'value', 'test2']].head(5))
print(f"Correlation: {df['value'].corr(df['test2']):.3f}\n")

# Formula 3: (cashes + top10s*2) / owgr
df['test3'] = (df['cashes'] + df['top10s']*2) / df['owgr']
print("Formula 3: (cashes + top10s*2) / owgr")
print(df[['player', 'cashes', 'top10s', 'owgr', 'value', 'test3']].head(5))
print(f"Correlation: {df['value'].corr(df['test3']):.3f}\n")

# Formula 4: (cashes*0.5 + top10s*2) / owgr
df['test4'] = (df['cashes']*0.5 + df['top10s']*2) / df['owgr']
print("Formula 4: (cashes*0.5 + top10s*2) / owgr")
print(df[['player', 'cashes', 'top10s', 'owgr', 'value', 'test4']].head(5))
print(f"Correlation: {df['value'].corr(df['test4']):.3f}\n")

# Formula 5: earnings / (owgr * 10000)
df['test5'] = df['earnings'] / (df['owgr'] * 10000)
print("Formula 5: earnings / (owgr * 10000)")
print(df[['player', 'earnings', 'owgr', 'value', 'test5']].head(5))
print(f"Correlation: {df['value'].corr(df['test5']):.3f}\n")

# Formula 6: (earnings / 100000) / owgr
df['test6'] = (df['earnings'] / 100000) / df['owgr']
print("Formula 6: (earnings / 100000) / owgr")
print(df[['player', 'earnings', 'owgr', 'value', 'test6']].head(5))
print(f"Correlation: {df['value'].corr(df['test6']):.3f}\n")

# Find the best correlation
correlations = {
    'test1: cashes/owgr': df['value'].corr(df['test1']),
    'test2: (cashes+top10s)/owgr': df['value'].corr(df['test2']),
    'test3: (cashes+top10s*2)/owgr': df['value'].corr(df['test3']),
    'test4: (cashes*0.5+top10s*2)/owgr': df['value'].corr(df['test4']),
    'test5: earnings/(owgr*10000)': df['value'].corr(df['test5']),
    'test6: (earnings/100000)/owgr': df['value'].corr(df['test6']),
}

print("\n" + "=" * 100)
print("CORRELATION SUMMARY")
print("=" * 100)
for formula, corr in sorted(correlations.items(), key=lambda x: x[1], reverse=True):
    print(f"{formula}: {corr:.3f}")
