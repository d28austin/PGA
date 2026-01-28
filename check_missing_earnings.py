"""
Check which tournaments are missing earnings data
"""

import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

# Find tournaments with no earnings data
cursor.execute('''
    SELECT
        tournament_name,
        COUNT(*) as total_players,
        SUM(CASE WHEN earnings IS NOT NULL AND earnings > 0 THEN 1 ELSE 0 END) as players_with_earnings
    FROM tournament_results
    WHERE year = 2024
    AND tournament_id != 'T001'
    GROUP BY tournament_name
    ORDER BY tournament_name
''')

results = cursor.fetchall()

print('=' * 80)
print('2024 TOURNAMENTS - EARNINGS STATUS')
print('=' * 80)
print()

no_earnings = []
partial_earnings = []
full_earnings = []

for name, total, with_earn in results:
    with_earn = with_earn if with_earn else 0
    pct = (with_earn / total * 100) if total > 0 else 0

    if with_earn == 0:
        no_earnings.append((name, total))
    elif pct < 90:
        partial_earnings.append((name, total, with_earn, pct))
    else:
        full_earnings.append((name, total, with_earn, pct))

print(f'Tournaments with NO earnings data: {len(no_earnings)}')
print('-' * 80)
for name, total in no_earnings:
    print(f'  {name:55} | {total:3} players')

print()
print(f'Tournaments with PARTIAL earnings data: {len(partial_earnings)}')
print('-' * 80)
for name, total, with_earn, pct in partial_earnings:
    print(f'  {name:55} | {with_earn}/{total} ({pct:.0f}%)')

print()
print(f'Tournaments with FULL earnings data: {len(full_earnings)}')
print(f'  (Not listing {len(full_earnings)} tournaments with >90% earnings)')

print()
print('=' * 80)
print('SUMMARY')
print('=' * 80)
print(f'  Total tournaments: {len(results)}')
print(f'  With NO earnings: {len(no_earnings)}')
print(f'  With PARTIAL earnings: {len(partial_earnings)}')
print(f'  With FULL earnings: {len(full_earnings)}')

conn.close()
