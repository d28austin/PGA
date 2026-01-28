"""
Check Jon Rahm's 2022 Farmers Insurance Open result
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

# Get Jon Rahm's 2022 Farmers Insurance Open result
df = pd.read_sql('''
    SELECT player_name, year, tournament_name, tournament_id, position, total_score, earnings
    FROM tournament_results
    WHERE player_name = 'Jon Rahm'
    AND tournament_name LIKE '%Farmers%'
    AND year = 2022
''', conn)

print('=' * 80)
print('JON RAHM - FARMERS INSURANCE OPEN 2022')
print('=' * 80)
print()

if not df.empty:
    for _, row in df.iterrows():
        print(f'Player: {row["player_name"]}')
        print(f'Year: {row["year"]}')
        print(f'Tournament: {row["tournament_name"]}')
        print(f'Tournament ID: {row["tournament_id"]}')
        print(f'Position: {row["position"]}')
        print(f'Total Score: {row["total_score"]}')
        print(f'Earnings: {row["earnings"]}')
        print()

        # Check if made cut
        position_numeric = pd.to_numeric(row['position'], errors='coerce')
        total_score_numeric = pd.to_numeric(row['total_score'], errors='coerce')
        tournament_par = 288
        min_reasonable_score = tournament_par * 0.75
        made_cut = (position_numeric <= 70) and (total_score_numeric >= min_reasonable_score)

        print(f'Made cut (pos <= 70 and score >= {min_reasonable_score}): {made_cut}')
        print()
else:
    print('No record found')
    print()

# Also check all 2022 Farmers results to see earnings coverage
print('=' * 80)
print('2022 FARMERS INSURANCE OPEN - TOP 20 FINISHERS')
print('=' * 80)
print()

all_results = pd.read_sql('''
    SELECT player_name, position, total_score, earnings
    FROM tournament_results
    WHERE tournament_name LIKE '%Farmers%'
    AND year = 2022
    ORDER BY CAST(position AS INTEGER)
    LIMIT 20
''', conn)

if not all_results.empty:
    for _, row in all_results.iterrows():
        earnings_str = f'${row["earnings"]:,.0f}' if pd.notna(row['earnings']) and row['earnings'] > 0 else 'NO EARNINGS'
        print(f'{row["player_name"]:25} | Pos: {row["position"]:3} | Score: {row["total_score"]:3} | {earnings_str}')

# Check total earnings coverage for 2022 Farmers
print()
print('=' * 80)
print('2022 FARMERS INSURANCE OPEN - EARNINGS COVERAGE')
print('=' * 80)
print()

all_2022 = pd.read_sql('''
    SELECT *
    FROM tournament_results
    WHERE tournament_name LIKE '%Farmers%'
    AND year = 2022
''', conn)

total = len(all_2022)
with_earnings = (all_2022['earnings'].notna() & (all_2022['earnings'] > 0)).sum()
print(f'Total players: {total}')
print(f'With earnings: {with_earnings}')
print(f'Without earnings: {total - with_earnings}')
print(f'Coverage: {with_earnings/total*100:.1f}%')

conn.close()
