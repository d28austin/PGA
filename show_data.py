"""
Display scraped PGA data in a nice table
"""

import sqlite3
import pandas as pd

# Set pandas display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)

conn = sqlite3.connect('data/cache/pga_data.db')

print("=" * 100)
print("PGA DATA SUMMARY")
print("=" * 100)

# Overall statistics
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM tournament_results')
total_results = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT tournament_id) FROM tournament_results')
total_tournaments = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT player_name) FROM tournament_results')
total_players = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT year) FROM tournament_results')
total_years = cursor.fetchone()[0]

print(f"\nTotal Statistics:")
print(f"  Total Player Results: {total_results}")
print(f"  Unique Tournaments: {total_tournaments}")
print(f"  Unique Players: {total_players}")
print(f"  Years with Data: {total_years}")

# Data by year
print("\n" + "=" * 100)
print("RESULTS BY YEAR")
print("=" * 100)
year_query = """
SELECT
    year,
    COUNT(*) as total_results,
    COUNT(DISTINCT tournament_id) as tournaments,
    COUNT(DISTINCT player_name) as players
FROM tournament_results
GROUP BY year
ORDER BY year DESC
"""
year_df = pd.read_sql(year_query, conn)
print(year_df.to_string(index=False))

# Tournament details
print("\n" + "=" * 100)
print("TOURNAMENTS WITH DATA")
print("=" * 100)
tournament_query = """
SELECT
    t.tournament_name,
    t.year,
    COUNT(tr.id) as player_count,
    MIN(CAST(tr.position AS INTEGER)) as best_position,
    MAX(CAST(tr.position AS INTEGER)) as worst_position
FROM tournaments t
LEFT JOIN tournament_results tr ON t.tournament_id = tr.tournament_id AND t.year = tr.year
WHERE tr.id IS NOT NULL
GROUP BY t.tournament_name, t.year
ORDER BY t.year DESC, t.tournament_name
"""
tournament_df = pd.read_sql(tournament_query, conn)
print(tournament_df.to_string(index=False))

# Top players by appearances
print("\n" + "=" * 100)
print("TOP 20 PLAYERS BY APPEARANCES")
print("=" * 100)
player_query = """
SELECT
    player_name,
    COUNT(*) as appearances,
    AVG(CAST(position AS REAL)) as avg_finish,
    MIN(CAST(position AS INTEGER)) as best_finish
FROM tournament_results
WHERE position IS NOT NULL AND position != ''
GROUP BY player_name
ORDER BY appearances DESC
LIMIT 20
"""
player_df = pd.read_sql(player_query, conn)
player_df['avg_finish'] = player_df['avg_finish'].round(1)
print(player_df.to_string(index=False))

# Sample of actual data
print("\n" + "=" * 100)
print("SAMPLE DATA (First 20 Results)")
print("=" * 100)
sample_query = """
SELECT
    player_name,
    tournament_id,
    year,
    position,
    total_score
FROM tournament_results
ORDER BY year DESC, tournament_id, CAST(position AS INTEGER)
LIMIT 20
"""
sample_df = pd.read_sql(sample_query, conn)
print(sample_df.to_string(index=False))

conn.close()

print("\n" + "=" * 100)
print("END OF DATA SUMMARY")
print("=" * 100)
