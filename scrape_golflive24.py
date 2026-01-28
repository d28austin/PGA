"""
Scrape OWGR rankings from golflive24.com
"""

import requests
from bs4 import BeautifulSoup
import re
import sqlite3
from datetime import datetime
import time

def scrape_golflive24_owgr():
    """Scrape OWGR from golflive24.com"""

    url = "https://www.golflive24.com/rankings/owgr/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print("Fetching golflive24.com OWGR rankings...")
    print()

    try:
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"Failed: status {response.status_code}")
            return {}

        # Try to find API endpoint in page source
        page_source = response.text

        # Look for API calls or data embedded in JavaScript
        # Common patterns: "rankings":[...], "players":[...], etc

        # Try to find JSON data in script tags
        soup = BeautifulSoup(page_source, 'html.parser')
        scripts = soup.find_all('script')

        print(f"Found {len(scripts)} script tags, analyzing...")
        print()

        rankings = {}

        for script in scripts:
            script_content = script.string
            if not script_content:
                continue

            # Look for JSON-like structures with ranking data
            # Pattern: "position":1,"name":"Scottie Scheffler"
            # or: "rank":1,"player":"Scottie Scheffler"

            # Try to find player/ranking pairs
            rank_matches = re.findall(r'"(?:position|rank|ranking)"\s*:\s*(\d+)', script_content)
            name_matches = re.findall(r'"(?:name|player|fullName|playerName)"\s*:\s*"([^"]+)"', script_content)

            if rank_matches and name_matches:
                print(f"Found potential data: {len(rank_matches)} ranks, {len(name_matches)} names")

                for i in range(min(len(rank_matches), len(name_matches))):
                    try:
                        rank = int(rank_matches[i])
                        name = name_matches[i]
                        if name and rank > 0 and len(name) > 3:
                            rankings[name] = rank
                    except:
                        continue

        if rankings:
            return rankings

        # If not found, try with Selenium
        print("No data found in static HTML, trying Selenium...")
        return scrape_with_selenium()

    except Exception as e:
        print(f"Error: {e}")
        return {}


def scrape_with_selenium():
    """Use Selenium to scrape after JavaScript loads"""

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("Selenium not available")
        return {}

    print()
    print("Using Selenium...")

    rankings = {}

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get('https://www.golflive24.com/rankings/owgr/')

        print("Waiting for page to load...")
        time.sleep(8)

        # Get page text
        page_text = driver.page_source

        # Save for debugging
        with open('golflive24_source.html', 'w', encoding='utf-8') as f:
            f.write(page_text)

        # Try to find table rows
        rows = driver.find_elements(By.TAG_NAME, "tr")
        print(f"Found {len(rows)} table rows")

        if len(rows) > 10:
            print("Sample rows:")
            for i, row in enumerate(rows[1:6]):  # Skip header, show first 5
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    print(f"  Row {i}: {[c.text[:30] for c in cells[:5]]}")

                    # Try to extract rank and name
                    try:
                        rank_text = cells[0].text.strip()
                        name_text = None

                        # Name is usually in columns 1, 2, or 3
                        for idx in [1, 2, 3]:
                            if idx < len(cells):
                                text = cells[idx].text.strip()
                                if text and len(text) > 3 and not text.replace('.', '').isdigit():
                                    name_text = text
                                    break

                        if rank_text and name_text:
                            rank = int(rank_text.replace('.', ''))
                            rankings[name_text] = rank

                    except:
                        pass

        # Also try div-based layout
        if not rankings:
            divs = driver.find_elements(By.CLASS_NAME, "ranking-row")
            print(f"Found {len(divs)} ranking divs")

            for div in divs[:50]:  # First 50
                try:
                    rank_elem = div.find_element(By.CLASS_NAME, "rank")
                    name_elem = div.find_element(By.CLASS_NAME, "player-name")

                    rank = int(rank_elem.text.strip())
                    name = name_elem.text.strip()

                    if rank and name:
                        rankings[name] = rank
                except:
                    continue

        driver.quit()

    except Exception as e:
        print(f"Selenium error: {e}")

    return rankings


def save_owgr_to_database(rankings, db_path='data/cache/pga_data.db'):
    """Save OWGR rankings to database"""

    if not rankings:
        print("No rankings to save")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owgr_rankings (
            player_name TEXT PRIMARY KEY,
            ranking INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    timestamp = datetime.now().isoformat()

    for player_name, ranking in rankings.items():
        cursor.execute("""
            INSERT OR REPLACE INTO owgr_rankings
            (player_name, ranking, last_updated)
            VALUES (?, ?, ?)
        """, (player_name, ranking, timestamp))

    conn.commit()
    conn.close()

    print()
    print(f"[OK] Saved {len(rankings)} rankings to database")
    print(f"Last updated: {timestamp}")


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR SCRAPER - GOLFLIVE24.COM")
    print("=" * 80)
    print()

    rankings = scrape_golflive24_owgr()

    if rankings:
        print()
        print(f"Successfully scraped {len(rankings)} players!")
        print()

        print("Top 15 players:")
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
        for player, rank in sorted_rankings[:15]:
            print(f"  #{rank}: {player}")

        # Check for Matthieu Pavon
        if "Matthieu Pavon" in rankings:
            print()
            print(f"[OK] Matthieu Pavon: #{rankings['Matthieu Pavon']}")

        save_owgr_to_database(rankings)

    else:
        print()
        print("Failed to scrape rankings")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
