import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

# Check scores for each tournament
for tid in ['401580329', '401580330', '401580331', '401580332', '401580333']:
    cursor.execute('''
        SELECT player_name, position, total_score
        FROM tournament_results
        WHERE tournament_id = ? AND CAST(position AS INTEGER) <= 5
        ORDER BY CAST(position AS INTEGER)
    ''', (tid,))

    print(f"\nTournament {tid}:")
    for row in cursor.fetchall():
        print(f"  {row[1]:>3}. {row[0]:25s} Score: {row[2]}")

conn.close()
