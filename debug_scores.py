"""
Debug the score data issues
"""

import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

tournaments = [
    ('401580329', 'The Sentry'),
    ('401580330', 'Sony Open in Hawaii'),
    ('401580331', 'The American Express'),
    ('401580332', 'Farmers Insurance Open'),
    ('401580333', 'AT&T Pebble Beach Pro-Am'),
]

for tid, name in tournaments:
    print(f"\n{'=' * 80}")
    print(f"{name} ({tid})")
    print('=' * 80)

    # Get top 5 finishers
    cursor.execute('''
        SELECT player_name, position, total_score
        FROM tournament_results
        WHERE tournament_id = ?
        AND CAST(position AS INTEGER) > 0
        AND CAST(position AS INTEGER) <= 5
        ORDER BY CAST(position AS INTEGER)
    ''', (tid,))

    print("\nTop 5 finishers:")
    for row in cursor.fetchall():
        print(f"  {row[1]:>3}. {row[0]:30s} Score: {row[2]}")

    # Get all scores to see the range
    cursor.execute('''
        SELECT MIN(CAST(total_score AS REAL)), MAX(CAST(total_score AS REAL)),
               AVG(CAST(total_score AS REAL)), COUNT(*)
        FROM tournament_results
        WHERE tournament_id = ?
        AND CAST(position AS INTEGER) > 0
        AND total_score IS NOT NULL
    ''', (tid,))

    min_s, max_s, avg_s, count = cursor.fetchone()
    print(f"\nScore range: {min_s:.0f} to {max_s:.0f}, Average: {avg_s:.1f}, Count: {count}")

conn.close()
