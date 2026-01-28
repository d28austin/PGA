"""
Fetch OWGR rankings from ESPN and store in database
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from data.database import PGADatabase

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

                    # Extract just the number from rank
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
    print("FETCHING AND STORING OWGR DATA")
    print("=" * 80)

    # Scrape OWGR data
    df = scrape_espn_owgr()

    if df is not None and not df.empty:
        print(f"\nTop 10 players:")
        print(df.head(10).to_string(index=False))

        # Save to database
        db = PGADatabase()
        db.save_owgr_rankings(df)

        print(f"\n\nSuccessfully saved {len(df)} rankings to database")

        # Test some lookups
        test_names = ['Scottie Scheffler', 'Chris Kirk', 'Rory McIlroy']
        print(f"\n\nTest lookups:")
        for name in test_names:
            rank = db.get_player_owgr(name)
            if rank:
                print(f"  {name}: #{rank}")
            else:
                print(f"  {name}: Not found")

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
