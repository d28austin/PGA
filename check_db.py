import sqlite3

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

# Check years
cursor.execute('SELECT DISTINCT year, COUNT(*) FROM tournament_results GROUP BY year')
print('Years in database:')
for row in cursor.fetchall():
    print(f'  Year {row[0]}: {row[1]} results')

# Check tournament IDs
cursor.execute('SELECT DISTINCT tournament_id FROM tournament_results LIMIT 10')
print('\nSample tournament IDs:')
for row in cursor.fetchall():
    print(f'  {row[0]}')

# Check a sample result
cursor.execute('SELECT * FROM tournament_results LIMIT 3')
print('\nSample results:')
for row in cursor.fetchall():
    print(f'  {row}')

conn.close()
