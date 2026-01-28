"""
Scrape OWGR data from ESPN
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def scrape_espn_owgr():
    """Scrape OWGR rankings from ESPN"""
    url = "https://www.espn.com/golf/rankings"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print("Fetching OWGR data from ESPN...")
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the rankings table
    table = soup.find('table', class_='Table')

    if not table:
        print("Could not find rankings table")
        return None

    rankings = []

    # Find all rows in the table body
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')

        for row in rows:
            cols = row.find_all('td')

            if len(cols) >= 2:
                # First column is rank
                rank_text = cols[0].get_text(strip=True)

                # Second column has player name (in an anchor tag)
                name_cell = cols[1]
                name_link = name_cell.find('a')

                if name_link:
                    player_name = name_link.get_text(strip=True)

                    # Extract just the number from rank (might have arrows/changes)
                    rank_match = re.search(r'\d+', rank_text)
                    if rank_match:
                        rank = int(rank_match.group())

                        rankings.append({
                            'rank': rank,
                            'player_name': player_name
                        })

    df = pd.DataFrame(rankings)
    print(f"Successfully scraped {len(df)} player rankings")

    return df

if __name__ == "__main__":
    print("=" * 80)
    print("SCRAPING OWGR DATA FROM ESPN")
    print("=" * 80)

    df = scrape_espn_owgr()

    if df is not None and not df.empty:
        print(f"\nTop 20 players:")
        print(df.head(20).to_string(index=False))

        print(f"\n\nTotal rankings retrieved: {len(df)}")

        # Test lookup
        test_names = ['Scottie Scheffler', 'Rory McIlroy', 'Chris Kirk']
        print(f"\n\nTest lookups:")
        for name in test_names:
            result = df[df['player_name'].str.contains(name, case=False, na=False)]
            if not result.empty:
                print(f"  {name}: Rank {result.iloc[0]['rank']}")
            else:
                print(f"  {name}: Not found")

    print("\n" + "=" * 80)
