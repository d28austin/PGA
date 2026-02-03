"""
ESPN Player Stats Scraper
Pulls comprehensive PGA player statistics for regression analysis

Available stat categories on ESPN:
- Scoring Average
- Driving Distance
- Driving Accuracy
- Greens in Regulation
- Putting Average
- Sand Save %
- Scrambling %
- Birdie Average
- Eagles (Holes per)
- Top 10 Finishes
- Money Leaders
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict
import time
import sqlite3
from datetime import datetime


class ESPNStatsScaper:
    """Scrape player statistics from ESPN"""

    def __init__(self):
        self.base_url = "https://www.espn.com/golf/stats/player/_/season/{year}/stat/{stat}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Stat categories available on ESPN
        self.stat_categories = {
            'scoring': 'Scoring Average',
            'drivingDistance': 'Driving Distance',
            'drivingAccuracy': 'Driving Accuracy',
            'greens': 'Greens in Regulation',
            'putting': 'Putting Average',
            'sandSaves': 'Sand Save Percentage',
            'scrambling': 'Scrambling',
            'birdies': 'Birdie Average',
            'eagles': 'Eagles (Holes per)',
            'top10': 'Top 10 Finishes'
        }

    def scrape_stat_category(self, year: int, stat_key: str) -> pd.DataFrame:
        """
        Scrape a specific stat category for a season

        Args:
            year: Season year
            stat_key: Stat category key (e.g., 'scoring', 'driving')

        Returns:
            DataFrame with player stats
        """
        url = self.base_url.format(year=year, stat=stat_key)

        try:
            print(f"Fetching {self.stat_categories.get(stat_key, stat_key)} for {year}...")

            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the stats table
            table = soup.find('table', class_='Table')

            if not table:
                print(f"  No table found for {stat_key}")
                return pd.DataFrame()

            # Parse table headers
            headers = []
            thead = table.find('thead')
            if thead:
                for th in thead.find_all('th'):
                    headers.append(th.get_text(strip=True))

            # Parse table rows
            rows = []
            tbody = table.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    row_data = []
                    for td in tr.find_all('td'):
                        row_data.append(td.get_text(strip=True))
                    if row_data:
                        rows.append(row_data)

            if not headers or not rows:
                print(f"  Could not parse table for {stat_key}")
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(rows, columns=headers)

            # Add metadata
            df['year'] = year
            df['stat_category'] = stat_key

            print(f"  Found {len(df)} players")
            return df

        except Exception as e:
            print(f"  Error: {e}")
            return pd.DataFrame()

    def scrape_all_stats(self, years: List[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape all stat categories for multiple years

        Args:
            years: List of years to scrape (default: last 3 years)

        Returns:
            Dictionary of DataFrames by stat category
        """
        if years is None:
            current_year = datetime.now().year
            years = [current_year, current_year - 1, current_year - 2]

        all_stats = {}

        for stat_key, stat_name in self.stat_categories.items():
            print(f"\n{'='*60}")
            print(f"Scraping {stat_name}")
            print(f"{'='*60}")

            stat_dfs = []

            for year in years:
                df = self.scrape_stat_category(year, stat_key)
                if not df.empty:
                    stat_dfs.append(df)
                time.sleep(1)  # Be respectful

            if stat_dfs:
                combined_df = pd.concat(stat_dfs, ignore_index=True)
                all_stats[stat_key] = combined_df
                print(f"Total records: {len(combined_df)}")

        return all_stats

    def save_to_database(self, stats_dict: Dict[str, pd.DataFrame], db_path: str = "data/cache/pga_data.db"):
        """
        Save stats to database

        Args:
            stats_dict: Dictionary of stat DataFrames
            db_path: Path to database
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create player_stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    stat_category TEXT NOT NULL,
                    rank INTEGER,
                    stat_value REAL,
                    events INTEGER,
                    raw_data TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_name, year, stat_category)
                )
            """)

            total_inserted = 0

            for stat_key, df in stats_dict.items():
                print(f"\nSaving {stat_key} to database...")

                for _, row in df.iterrows():
                    try:
                        # Extract player name (usually first column)
                        player_name = row.iloc[0] if len(row) > 0 else None
                        year = row.get('year')

                        # Try to extract rank and stat value
                        rank = None
                        stat_value = None

                        # Rank is often in 'RK' or first numeric column
                        if 'RK' in row:
                            try:
                                rank = int(row['RK'])
                            except:
                                pass

                        # Stat value is usually in a column with the stat name
                        for col in df.columns:
                            if col not in ['PLAYER', 'RK', 'year', 'stat_category']:
                                try:
                                    stat_value = float(row[col].replace('%', '').replace(',', ''))
                                    break
                                except:
                                    continue

                        if player_name and year:
                            cursor.execute("""
                                INSERT OR REPLACE INTO player_stats
                                (player_name, year, stat_category, rank, stat_value, raw_data)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                player_name,
                                year,
                                stat_key,
                                rank,
                                stat_value,
                                str(row.to_dict())
                            ))
                            total_inserted += 1

                    except Exception as e:
                        continue

            conn.commit()
            conn.close()

            print(f"\n{'='*60}")
            print(f"Database updated: {total_inserted} records saved")
            print(f"{'='*60}")

        except Exception as e:
            print(f"Error saving to database: {e}")


def main():
    """Main function to scrape ESPN stats"""
    print("\n" + "="*60)
    print("ESPN PLAYER STATS SCRAPER - FULL HISTORICAL DATA")
    print("="*60)
    print("\nThis will scrape player statistics from ESPN for")
    print("regression analysis and model optimization.")
    print()

    # Scrape ALL historical data from 2014-2026
    years = list(range(2014, 2027))  # 2014 through 2026
    print(f"Scraping years: {years[0]}-{years[-1]} ({len(years)} years)")
    print(f"This will take approximately {len(years) * 10} seconds (being respectful to ESPN)...")
    print()

    scraper = ESPNStatsScaper()

    # Scrape all stats
    stats_dict = scraper.scrape_all_stats(years=years)

    if stats_dict:
        # Save to database
        scraper.save_to_database(stats_dict)

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        for stat_key, df in stats_dict.items():
            print(f"{stat_key}: {len(df)} records")

        print("\nStats are now available for:")
        print("- Regression analysis")
        print("- Model optimization")
        print("- Enhanced recommendations")
    else:
        print("\nNo stats scraped. Check ESPN website structure.")


if __name__ == "__main__":
    main()
