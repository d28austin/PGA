"""
Debug the earnings scraper to see why it's not finding earnings
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_scrape(tournament_id):
    """Debug scraping to see what's happening"""

    url = f"https://www.espn.com/golf/leaderboard/_/tournamentId/{tournament_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"Fetching: {url}")
    print()

    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status code: {response.status_code}")
    print()

    if response.status_code != 200:
        print("Failed to fetch page")
        return

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the leaderboard table
    table = soup.find('table', class_='Table')

    if not table:
        print("No table found with class='Table'")
        # Try to find any tables
        all_tables = soup.find_all('table')
        print(f"Found {len(all_tables)} tables total")
        return

    print("Found table with class='Table'")
    print()

    # Find table body
    tbody = table.find('tbody')

    if not tbody:
        print("No tbody found")
        return

    print("Found tbody")
    print()

    rows = tbody.find_all('tr', class_='Table__TR')
    print(f"Found {len(rows)} rows with class='Table__TR'")
    print()

    # Look at first row in detail
    if len(rows) > 0:
        print("=" * 80)
        print("ANALYZING FIRST ROW")
        print("=" * 80)

        row = rows[0]
        cells = row.find_all('td')

        print(f"Number of cells: {len(cells)}")
        print()

        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            print(f"Cell {i}: {text[:100] if len(text) > 100 else text}")

        print()
        print("=" * 80)
        print("CHECKING FOR EARNINGS")
        print("=" * 80)

        # Check which cell has earnings
        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            if '$' in text:
                print(f"Found $ in cell {i}: {text}")

if __name__ == "__main__":
    print("=" * 80)
    print("DEBUG: 2022 Farmers Insurance Open")
    print("=" * 80)
    print()

    debug_scrape('401353234')
