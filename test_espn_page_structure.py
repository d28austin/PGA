"""
Test ESPN page structure to understand the table format
"""

import requests
from bs4 import BeautifulSoup

tournament_id = '401580329'
url = f"https://www.espn.com/golf/leaderboard/_/tournamentId/{tournament_id}"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Find the table
table = soup.find('table', class_='Table')

if table:
    print("Found table!")

    # Get first row to understand structure
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr', class_='Table__TR')
        if rows:
            print(f"\nFound {len(rows)} rows")
            print("\nFirst row structure:")

            first_row = rows[0]
            cells = first_row.find_all('td')

            print(f"Number of cells: {len(cells)}")

            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                has_link = cell.find('a') is not None
                classes = cell.get('class', [])
                print(f"  Cell {i}: '{text[:50]}' | Has link: {has_link} | Classes: {classes}")

            # Try to find player name more specifically
            print("\n\nSearching for player name cell:")
            for i, cell in enumerate(cells):
                if cell.find('a', class_='AnchorLink'):
                    print(f"  Found AnchorLink in cell {i}: {cell.get_text(strip=True)}")
