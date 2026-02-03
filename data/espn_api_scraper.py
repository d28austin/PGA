"""
ESPN Player Stats Scraper - Using Backend API
Pulls comprehensive PGA player statistics via ESPN's JSON API
"""

import requests
import pandas as pd
import sqlite3
from typing import List, Dict
from datetime import datetime
import time


class ESPNAPIScraper:
    """Scrape player statistics using ESPN's backend API"""

    def __init__(self):
        self.api_url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_season_stats(self, year: int) -> Dict:
        """
        Fetch all statistics for a season from ESPN API

        Args:
            year: Season year

        Returns:
            Dictionary containing parsed stats
        """
        print(f"\nFetching statistics for {year}...")

        try:
            response = requests.get(
                self.api_url,
                params={'season': year},
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()

            if 'stats' not in data:
                print(f"  No stats found for {year}")
                return {}

            stats = data['stats']
            categories = stats.get('categories', [])

            print(f"  Found {len(categories)} stat categories")

            # Parse each category
            all_stats = {}

            for category in categories:
                cat_name = category.get('name', 'unknown')
                display_name = category.get('displayName', cat_name)
                leaders = category.get('leaders', [])

                print(f"    {display_name}: {len(leaders)} players")

                if leaders:
                    all_stats[cat_name] = {
                        'displayName': display_name,
                        'leaders': leaders
                    }

            return all_stats

        except Exception as e:
            print(f"  Error: {e}")
            return {}

    def parse_player_stats(self, player_data: Dict, stat_category: str, year: int) -> Dict:
        """
        Parse individual player statistics from API response

        Args:
            player_data: Player data from API
            stat_category: Stat category name
            year: Season year

        Returns:
            Dictionary with parsed player stats
        """
        athlete = player_data.get('athlete', {})
        player_id = athlete.get('id')
        player_name = athlete.get('displayName', 'Unknown')

        # Get primary stat value
        stat_value = player_data.get('value')
        stat_display = player_data.get('displayValue', str(stat_value))

        # Try to extract rank (may not always be present in main data)
        rank = player_data.get('rank')

        # Look in embedded statistics for more details
        statistics = player_data.get('statistics', {})
        if statistics:
            splits = statistics.get('splits', {})
            if splits:
                categories = splits.get('categories', [])
                if categories:
                    # Find matching stat in embedded data
                    for cat in categories:
                        for stat in cat.get('stats', []):
                            if stat.get('name') == stat_category:
                                if not rank:
                                    rank = stat.get('rank')
                                if not stat_value:
                                    stat_value = stat.get('value')
                                break

        return {
            'player_id': player_id,
            'player_name': player_name,
            'year': year,
            'stat_category': stat_category,
            'stat_value': stat_value,
            'stat_display': stat_display,
            'rank': rank
        }

    def scrape_multiple_years(self, years: List[int]) -> pd.DataFrame:
        """
        Scrape statistics for multiple years

        Args:
            years: List of years to scrape

        Returns:
            DataFrame with all scraped stats
        """
        all_rows = []

        for year in years:
            year_stats = self.fetch_season_stats(year)

            if not year_stats:
                continue

            # Process each stat category
            for stat_key, stat_data in year_stats.items():
                leaders = stat_data.get('leaders', [])

                for leader in leaders:
                    parsed = self.parse_player_stats(leader, stat_key, year)
                    all_rows.append(parsed)

            # Be respectful to API
            time.sleep(1)

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)
        print(f"\nTotal records scraped: {len(df)}")
        return df

    def save_to_database(self, df: pd.DataFrame, db_path: str = "data/cache/pga_data.db"):
        """
        Save scraped stats to database

        Args:
            df: DataFrame with stats
            db_path: Path to database
        """
        if df.empty:
            print("No data to save")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id TEXT,
                    player_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    stat_category TEXT NOT NULL,
                    rank INTEGER,
                    stat_value REAL,
                    stat_display TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_id, year, stat_category)
                )
            """)

            # Insert data
            inserted = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO player_stats
                        (player_id, player_name, year, stat_category, rank, stat_value, stat_display)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('player_id'),
                        row['player_name'],
                        row['year'],
                        row['stat_category'],
                        row.get('rank'),
                        row.get('stat_value'),
                        row.get('stat_display')
                    ))
                    inserted += 1
                except Exception as e:
                    print(f"Error inserting {row.get('player_name')}: {e}")
                    continue

            conn.commit()
            conn.close()

            print(f"\nDatabase updated: {inserted} records saved to {db_path}")

        except Exception as e:
            print(f"Error saving to database: {e}")


def main():
    """Main function to run the scraper"""
    print("\n" + "="*80)
    print("ESPN PLAYER STATS SCRAPER - API VERSION")
    print("="*80)
    print("\nUsing ESPN's backend API for cleaner, faster data collection")
    print()

    scraper = ESPNAPIScraper()

    # Scrape recent years
    years = [2025, 2024, 2023]
    print(f"Scraping years: {years}")

    df = scraper.scrape_multiple_years(years)

    if not df.empty:
        # Show summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total players: {df['player_name'].nunique()}")
        print(f"Total records: {len(df)}")
        print(f"\nRecords per year:")
        print(df.groupby('year').size())
        print(f"\nRecords per category:")
        print(df.groupby('stat_category').size())

        # Save to database
        scraper.save_to_database(df)
    else:
        print("\nNo data scraped!")


if __name__ == "__main__":
    main()
