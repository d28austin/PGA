"""
Check which 2022 tournaments have earnings data
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

# Get earnings coverage for each 2022 tournament
df = pd.read_sql('''
    SELECT
        tournament_name,
        COUNT(*) as total_players,
        SUM(CASE WHEN earnings IS NOT NULL AND earnings > 0 THEN 1 ELSE 0 END) as players_with_earnings
    FROM tournament_results
    WHERE year = 2022
    GROUP BY tournament_name
    ORDER BY players_with_earnings DESC, tournament_name
''', conn)

conn.close()

print('=' * 80)
print('2022 TOURNAMENTS - EARNINGS COVERAGE')
print('=' * 80)
print()

df['coverage_pct'] = (df['players_with_earnings'] / df['total_players'] * 100).round(0).astype(int)

no_earnings = df[df['players_with_earnings'] == 0]
partial_earnings = df[(df['players_with_earnings'] > 0) & (df['coverage_pct'] < 90)]
full_earnings = df[df['coverage_pct'] >= 90]

print(f'Tournaments with NO earnings: {len(no_earnings)}')
print('-' * 80)
if len(no_earnings) > 0:
    for _, row in no_earnings.iterrows():
        print(f'  {row["tournament_name"]:50} | {row["total_players"]:3} players')

print()
print(f'Tournaments with PARTIAL earnings (<90%): {len(partial_earnings)}')
print('-' * 80)
if len(partial_earnings) > 0:
    for _, row in partial_earnings.iterrows():
        print(f'  {row["tournament_name"]:50} | {row["players_with_earnings"]}/{row["total_players"]} ({row["coverage_pct"]}%)')

print()
print(f'Tournaments with FULL earnings (>=90%): {len(full_earnings)}')
print('-' * 80)
if len(full_earnings) > 0:
    for _, row in full_earnings.head(10).iterrows():
        print(f'  {row["tournament_name"]:50} | {row["players_with_earnings"]}/{row["total_players"]} ({row["coverage_pct"]}%)')
    if len(full_earnings) > 10:
        print(f'  ... and {len(full_earnings) - 10} more')

print()
print('=' * 80)
print('SUMMARY')
print('=' * 80)
total_tournaments = len(df)
print(f'Total tournaments: {total_tournaments}')
print(f'With NO earnings: {len(no_earnings)} ({len(no_earnings)/total_tournaments*100:.1f}%)')
print(f'With PARTIAL earnings: {len(partial_earnings)} ({len(partial_earnings)/total_tournaments*100:.1f}%)')
print(f'With FULL earnings: {len(full_earnings)} ({len(full_earnings)/total_tournaments*100:.1f}%)')
