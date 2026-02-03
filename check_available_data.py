"""
Quick script to check what historical data we have available
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')

print("="*60)
print("AVAILABLE DATA SOURCES")
print("="*60)

# 1. Tournament Results
print("\n1. TOURNAMENT RESULTS")
tr = pd.read_sql("""
    SELECT COUNT(*) as total_records,
           COUNT(DISTINCT player_name) as unique_players,
           COUNT(DISTINCT tournament_name) as unique_tournaments,
           MIN(year) as earliest_year,
           MAX(year) as latest_year
    FROM tournament_results
""", conn)
print(tr.to_string(index=False))

# 2. ESPN Player Stats
print("\n2. ESPN PLAYER STATS")
ps = pd.read_sql("""
    SELECT stat_category,
           COUNT(*) as records,
           COUNT(DISTINCT player_name) as players
    FROM player_stats
    GROUP BY stat_category
""", conn)
print(ps.to_string(index=False))

# Sample player to check data quality
print("\n3. SAMPLE DATA FOR SCOTTIE SCHEFFLER")
sample = pd.read_sql("""
    SELECT stat_category, year, stat_value, raw_data
    FROM player_stats
    WHERE raw_data LIKE '%Scottie Scheffler%'
    ORDER BY stat_category, year
    LIMIT 10
""", conn)
print(sample.to_string(index=False))

# 4. Check tournament results fields
print("\n4. TOURNAMENT RESULTS FIELDS")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(tournament_results)")
columns = cursor.fetchall()
print("Columns:", [col[1] for col in columns])

# 5. Recent form data availability
print("\n5. RECENT TOURNAMENT RESULTS (last 2 years)")
recent = pd.read_sql("""
    SELECT player_name,
           COUNT(*) as events,
           AVG(CASE WHEN position NOT LIKE '%CUT%' THEN 1 ELSE 0 END) as cut_rate,
           COUNT(CASE WHEN CAST(position AS INTEGER) <= 10 THEN 1 END) as top_10s
    FROM tournament_results
    WHERE year >= 2023
    AND position IS NOT NULL
    GROUP BY player_name
    ORDER BY events DESC
    LIMIT 5
""", conn)
print(recent.to_string(index=False))

# 6. OWGR Rankings
print("\n6. OWGR RANKINGS")
owgr = pd.read_sql("""
    SELECT COUNT(*) as total_records,
           COUNT(DISTINCT player_name) as unique_players
    FROM owgr_rankings
""", conn)
print(owgr.to_string(index=False))

conn.close()

print("\n" + "="*60)
print("SUMMARY: What data can be used for regression?")
print("="*60)
print("""
AVAILABLE FOR VALUE PREDICTION:
✓ Tournament-specific history (wins, top 10s, avg finish, appearances)
✓ Recent form (last 10-20 events across all tournaments)
✓ ESPN season stats (scoring, driving, greens, putting, etc.)
✓ OWGR rankings
✓ Scoring average at specific tournament
✓ Cut rate (tournament-specific and overall)

RECOMMENDATION:
Create enhanced regression model that includes:
1. Course-specific metrics (dominant: 50-60%)
2. Current season form (moderate: 20-25%)
3. Statistical profile (moderate: 15-20%)
""")
