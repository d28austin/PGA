"""
ESPN Full Player Stats Scraper
Uses individual player API to get all 52+ stats per player
"""

import requests
import sqlite3
import time
from typing import List, Dict
from datetime import datetime


class ESPNFullStatsScraper:
    """Scrape complete player statistics using ESPN's player-level API"""

    def __init__(self):
        self.athletes_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/athletes"
        self.player_stats_url = "http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/seasons/{year}/types/2/athletes/{player_id}/statistics/0"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_active_players(self, limit: int = 300) -> List[str]:
        """
        Get list of active PGA player IDs

        Args:
            limit: Number of players to fetch (default 300)

        Returns:
            List of player IDs
        """
        print(f"\nFetching active PGA players (limit: {limit})...")

        try:
            response = requests.get(
                self.athletes_url,
                params={'limit': limit, 'active': 'true'},
                timeout=15
            )
            response.raise_for_status()

            data = response.json()
            items = data.get('items', [])

            player_ids = []
            for item in items:
                ref = item.get('$ref', '')
                # Extract player ID from URL
                # Format: http://...../athletes/9478?lang=en&region=us
                if '/athletes/' in ref:
                    player_id = ref.split('/athletes/')[1].split('?')[0]
                    player_ids.append(player_id)

            print(f"  Found {len(player_ids)} players")
            return player_ids

        except Exception as e:
            print(f"  Error fetching players: {e}")
            return []

    def fetch_player_stats(self, player_id: str, year: int) -> Dict:
        """
        Fetch all stats for a player in a specific season

        Args:
            player_id: ESPN player ID
            year: Season year

        Returns:
            Dictionary with player stats
        """
        url = self.player_stats_url.format(year=year, player_id=player_id)

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 404:
                # Player didn't play in this season
                return None

            response.raise_for_status()
            data = response.json()

            # Extract player info
            athlete_ref = data.get('athlete', {}).get('$ref', '')

            # Extract stats
            splits = data.get('splits', {})
            if not splits:
                return None

            categories = splits.get('categories', [])
            if not categories:
                return None

            stats_list = categories[0].get('stats', [])
            if not stats_list:
                return None

            return {
                'player_id': player_id,
                'year': year,
                'stats': stats_list,
                'athlete_ref': athlete_ref
            }

        except Exception as e:
            return None

    def fetch_player_name(self, player_id: str) -> str:
        """Fetch player name from their profile"""
        url = f"http://sports.core.api.espn.com/v2/sports/golf/leagues/pga/athletes/{player_id}"

        try:
            response = requests.get(url, params={'lang': 'en', 'region': 'us'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('displayName', f'Player_{player_id}')
        except:
            pass

        return f'Player_{player_id}'

    def scrape_season(self, year: int, max_players: int = 300) -> List[Dict]:
        """
        Scrape stats for all players in a season

        Args:
            year: Season year
            max_players: Maximum number of players to fetch

        Returns:
            List of player stat dictionaries
        """
        print(f"\n{'='*80}")
        print(f"SCRAPING {year} SEASON")
        print(f"{'='*80}")

        # Get player IDs
        player_ids = self.get_active_players(limit=max_players)

        if not player_ids:
            print("No players found!")
            return []

        all_player_stats = []
        successful = 0
        failed = 0

        print(f"\nFetching stats for {len(player_ids)} players...")
        print("(This may take a few minutes - being respectful to API)")

        for i, player_id in enumerate(player_ids):
            # Progress indicator
            if (i + 1) % 25 == 0:
                print(f"  Progress: {i+1}/{len(player_ids)} players ({successful} successful, {failed} no data)")

            stats = self.fetch_player_stats(player_id, year)

            if stats:
                all_player_stats.append(stats)
                successful += 1
            else:
                failed += 1

            # Be respectful to API - small delay
            time.sleep(0.1)

        print(f"\n{'='*80}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*80}")
        print(f"  Successful: {successful} players")
        print(f"  No data: {failed} players")
        print(f"  Total stats records: {successful * 52} (approx)")

        return all_player_stats

    def save_to_database(self, player_stats_list: List[Dict], db_path: str = "data/cache/pga_data.db"):
        """
        Save player stats to database

        Args:
            player_stats_list: List of player stat dictionaries
            db_path: Path to database
        """
        if not player_stats_list:
            print("\nNo data to save")
            return

        print(f"\n{'='*80}")
        print("SAVING TO DATABASE")
        print(f"{'='*80}")

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create comprehensive stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_season_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id TEXT NOT NULL,
                    player_name TEXT,
                    year INTEGER NOT NULL,
                    stat_name TEXT NOT NULL,
                    stat_abbreviation TEXT,
                    stat_display_name TEXT,
                    stat_value REAL,
                    stat_display_value TEXT,
                    rank INTEGER,
                    rank_display_value TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_id, year, stat_name)
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_player_year_stat
                ON player_season_stats(player_id, year, stat_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stat_name
                ON player_season_stats(stat_name)
            """)

            inserted = 0
            players_processed = 0

            # Cache player names
            player_name_cache = {}

            for player_data in player_stats_list:
                player_id = player_data['player_id']
                year = player_data['year']
                stats = player_data['stats']

                # Get player name (with caching)
                if player_id not in player_name_cache:
                    player_name_cache[player_id] = self.fetch_player_name(player_id)
                    time.sleep(0.05)  # Small delay for name fetches

                player_name = player_name_cache[player_id]

                # Insert each stat
                for stat in stats:
                    stat_name = stat.get('name')
                    if not stat_name:
                        continue

                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO player_season_stats
                            (player_id, player_name, year, stat_name, stat_abbreviation,
                             stat_display_name, stat_value, stat_display_value,
                             rank, rank_display_value)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            player_id,
                            player_name,
                            year,
                            stat_name,
                            stat.get('abbreviation'),
                            stat.get('displayName'),
                            stat.get('value'),
                            stat.get('displayValue'),
                            stat.get('rank'),
                            stat.get('rankDisplayValue')
                        ))
                        inserted += 1
                    except Exception as e:
                        print(f"Error inserting stat {stat_name} for player {player_id}: {e}")
                        continue

                players_processed += 1

                # Commit periodically
                if players_processed % 50 == 0:
                    conn.commit()
                    print(f"  Saved {players_processed} players ({inserted} stat records)...")

            conn.commit()
            conn.close()

            print(f"\n{'='*80}")
            print(f"DATABASE UPDATED")
            print(f"{'='*80}")
            print(f"  Players: {players_processed}")
            print(f"  Total stats records: {inserted}")
            print(f"  Database: {db_path}")

        except Exception as e:
            print(f"Error saving to database: {e}")


def main():
    """Main function to run the scraper"""
    print("\n" + "="*80)
    print("ESPN FULL PLAYER STATS SCRAPER")
    print("="*80)
    print("\nUsing individual player API to get all 52+ stats per player")
    print()

    scraper = ESPNFullStatsScraper()

    # Scrape 2025 season (test with first 250 players)
    player_stats = scraper.scrape_season(year=2025, max_players=250)

    if player_stats:
        # Save to database
        scraper.save_to_database(player_stats)

        # Show sample
        print("\n" + "="*80)
        print("SAMPLE DATA VERIFICATION")
        print("="*80)

        if player_stats:
            sample = player_stats[0]
            print(f"\nPlayer ID: {sample['player_id']}")
            print(f"Year: {sample['year']}")
            print(f"Number of stats: {len(sample['stats'])}")
            print("\nFirst 10 stats:")
            for stat in sample['stats'][:10]:
                print(f"  {stat.get('abbreviation', 'N/A'):20s} {stat.get('displayName', 'N/A'):40s} {stat.get('displayValue', 'N/A')}")
    else:
        print("\nNo data scraped!")


if __name__ == "__main__":
    main()
