"""
Clean summary of scraped data
"""

import sqlite3
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

conn = sqlite3.connect('data/cache/pga_data.db')

print("=" * 120)
print("PGA DATA SUMMARY - WHAT WE HAVE")
print("=" * 120)

# Get valid 2024 data (exclude position = 0 which means not played yet)
query = """
SELECT
    tournament_id,
    year,
    COUNT(*) as player_count,
    MIN(player_name) as sample_player,
    MIN(CAST(position AS INTEGER)) as best_pos,
    MAX(CAST(position AS INTEGER)) as worst_pos
FROM tournament_results
WHERE CAST(position AS INTEGER) > 0
GROUP BY tournament_id, year
ORDER BY year DESC, tournament_id
"""
tournaments = pd.read_sql(query, conn)

print("\nTOURNAMENTS WITH COMPLETE DATA:")
print("-" * 120)
for _, row in tournaments.iterrows():
    print(f"Tournament: {row['tournament_id']} | Year: {row['year']} | Players: {row['player_count']} | Positions: {row['best_pos']}-{row['worst_pos']}")

# Show tournament names
print("\n" + "=" * 120)
print("DETAILED 2024 TOURNAMENT DATA")
print("=" * 120)

for _, row in tournaments.iterrows():
    if row['year'] == 2024:
        print(f"\nTournament ID: {row['tournament_id']}")

        # Get top 10 players
        query2 = f"""
        SELECT
            position,
            player_name,
            total_score
        FROM tournament_results
        WHERE tournament_id = '{row['tournament_id']}' AND year = {row['year']}
        ORDER BY CAST(position AS INTEGER)
        LIMIT 10
        """
        top10 = pd.read_sql(query2, conn)
        print(top10.to_string(index=False))

# Summary stats
print("\n" + "=" * 120)
print("SUMMARY STATISTICS")
print("=" * 120)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM tournament_results WHERE CAST(position AS INTEGER) > 0")
valid_results = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT player_name) FROM tournament_results WHERE CAST(position AS INTEGER) > 0")
unique_players = cursor.fetchone()[0]

print(f"\n✓ Total valid player results: {valid_results}")
print(f"✓ Unique players: {unique_players}")
print(f"✓ Tournaments with data: {len(tournaments)}")
print(f"✓ Years covered: 2024")

print("\n" + "=" * 120)
print("TOP 15 PLAYERS BY BEST AVERAGE FINISH (min 3 appearances)")
print("=" * 120)

query3 = """
SELECT
    player_name,
    COUNT(*) as tournaments,
    ROUND(AVG(CAST(position AS REAL)), 1) as avg_finish,
    MIN(CAST(position AS INTEGER)) as best_finish
FROM tournament_results
WHERE CAST(position AS INTEGER) > 0
GROUP BY player_name
HAVING COUNT(*) >= 3
ORDER BY avg_finish
LIMIT 15
"""
top_players = pd.read_sql(query3, conn)
print(top_players.to_string(index=False))

conn.close()

print("\n" + "=" * 120)
