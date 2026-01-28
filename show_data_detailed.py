"""
Show detailed raw data
"""

import sqlite3
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

conn = sqlite3.connect('data/cache/pga_data.db')

print("=" * 100)
print("2024 TOURNAMENT DATA (Sample from first tournament)")
print("=" * 100)

query = """
SELECT
    player_name,
    tournament_id,
    year,
    position,
    total_score,
    earnings
FROM tournament_results
WHERE year = 2024 AND tournament_id = '401580329'
ORDER BY CAST(position AS INTEGER)
LIMIT 30
"""
df = pd.read_sql(query, conn)
print(df.to_string(index=False))

print("\n" + "=" * 100)
print("2025 TOURNAMENT DATA (Recent fetch)")
print("=" * 100)

query2 = """
SELECT
    player_name,
    tournament_id,
    year,
    position,
    total_score,
    earnings
FROM tournament_results
WHERE year = 2025
ORDER BY id
LIMIT 30
"""
df2 = pd.read_sql(query2, conn)
print(df2.to_string(index=False))

print("\n" + "=" * 100)
print("TOURNAMENT LIST")
print("=" * 100)

query3 = """
SELECT
    tournament_id,
    tournament_name,
    year,
    start_date
FROM tournaments
WHERE year IN (2024, 2025)
ORDER BY year DESC, start_date DESC
LIMIT 10
"""
df3 = pd.read_sql(query3, conn)
print(df3.to_string(index=False))

conn.close()
