"""
Scrape OWGR (Official World Golf Ranking) data
"""

import requests
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime

def scrape_owgr_rankings(max_pages=12):
    """
    Scrape OWGR rankings from official website

    Args:
        max_pages: Number of pages to scrape (50 players per page)
                   12 pages = 600 players

    Returns:
        dict: {player_name: ranking}
    """

    rankings = {}
    base_url = "https://www.owgr.com/ranking"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"Scraping OWGR rankings (up to {max_pages * 50} players)...")
    print()

    for page in range(1, max_pages + 1):
        print(f"Page {page}/{max_pages}...", end=' ', flush=True)

        # OWGR uses page numbers in URL
        url = f"{base_url}?pageNo={page}&pageSize=50&country=All"

        try:
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"Failed (status {response.status_code})")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the ranking table
            table = soup.find('table', class_='table-styled')

            if not table:
                print("No table found")
                continue

            tbody = table.find('tbody')
            if not tbody:
                print("No tbody found")
                continue

            rows = tbody.find_all('tr')

            page_count = 0
            for row in rows:
                cells = row.find_all('td')

                if len(cells) < 3:
                    continue

                # Column 0: Rank
                rank_text = cells[0].get_text(strip=True)
                try:
                    rank = int(rank_text)
                except ValueError:
                    continue

                # Column 2: Player name
                player_name = cells[2].get_text(strip=True)

                if player_name:
                    rankings[player_name] = rank
                    page_count += 1

            print(f"OK ({page_count} players)")

            # Be nice to the server
            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            continue

    print()
    print(f"Total players scraped: {len(rankings)}")
    return rankings


def save_owgr_to_database(rankings, db_path='data/cache/pga_data.db'):
    """Save OWGR rankings to database"""

    if not rankings:
        print("No rankings to save")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create OWGR table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owgr_rankings (
            player_name TEXT PRIMARY KEY,
            ranking INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    # Update timestamp
    timestamp = datetime.now().isoformat()

    # Insert/update rankings
    updated = 0
    for player_name, ranking in rankings.items():
        cursor.execute("""
            INSERT OR REPLACE INTO owgr_rankings
            (player_name, ranking, last_updated)
            VALUES (?, ?, ?)
        """, (player_name, ranking, timestamp))
        updated += 1

    conn.commit()
    conn.close()

    print(f"Saved {updated} rankings to database")
    print(f"Last updated: {timestamp}")


def check_specific_player(player_name, db_path='data/cache/pga_data.db'):
    """Check if a specific player has OWGR ranking"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ranking, last_updated
        FROM owgr_rankings
        WHERE player_name = ?
    """, (player_name,))

    result = cursor.fetchone()
    conn.close()

    if result:
        print(f"{player_name}: Ranked #{result[0]} (updated: {result[1]})")
    else:
        print(f"{player_name}: Not found in database")


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR RANKINGS SCRAPER")
    print("=" * 80)
    print()

    # Scrape rankings (12 pages = 600 players)
    rankings = scrape_owgr_rankings(max_pages=12)

    if rankings:
        print()
        print("Sample rankings:")
        for i, (player, rank) in enumerate(list(rankings.items())[:10], 1):
            print(f"  #{rank}: {player}")

        print()
        print("=" * 80)
        print("SAVING TO DATABASE")
        print("=" * 80)
        print()

        save_owgr_to_database(rankings)

        print()
        print("=" * 80)
        print("CHECKING SPECIFIC PLAYERS")
        print("=" * 80)
        print()

        # Check Matthieu Pavon specifically
        check_specific_player("Matthieu Pavon")
        check_specific_player("Scottie Scheffler")
        check_specific_player("Rory McIlroy")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
