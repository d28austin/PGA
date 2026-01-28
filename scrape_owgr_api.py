"""
Scrape OWGR rankings by finding the API endpoint the website uses
"""

import requests
import json
import sqlite3
from datetime import datetime
import time

def fetch_owgr_via_api(page_size=200, max_pages=3):
    """
    Fetch OWGR rankings by calling the API endpoint directly
    The OWGR website uses an API to load data dynamically
    """

    rankings = {}

    # Try different possible API endpoints
    api_endpoints = [
        "https://www.owgr.com/api/ranking",
        "https://api.owgr.com/ranking",
        "https://www.owgr.com/rankings/api",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.owgr.com/ranking'
    }

    print("Searching for OWGR API endpoint...")
    print()

    for base_url in api_endpoints:
        print(f"Trying: {base_url}")

        for page in range(1, max_pages + 1):
            try:
                # Try different parameter formats
                param_formats = [
                    {'pageNo': page, 'pageSize': page_size, 'country': 'All'},
                    {'page': page, 'size': page_size},
                    {'offset': (page-1)*page_size, 'limit': page_size},
                ]

                for params in param_formats:
                    response = requests.get(base_url, params=params, headers=headers, timeout=10)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"  [OK] Found working endpoint with params: {params}")
                            print(f"  Response keys: {list(data.keys())[:5]}")

                            # Try to extract rankings
                            # Common structures: data.rankings, data.players, data.items, data (array)
                            items = None

                            if isinstance(data, list):
                                items = data
                            elif 'rankings' in data:
                                items = data['rankings']
                            elif 'players' in data:
                                items = data['players']
                            elif 'items' in data:
                                items = data['items']
                            elif 'data' in data:
                                if isinstance(data['data'], list):
                                    items = data['data']

                            if items:
                                print(f"  Found {len(items)} items")
                                print(f"  Sample item keys: {list(items[0].keys())[:10]}")

                                for item in items:
                                    # Try different key names
                                    rank = None
                                    name = None

                                    for rank_key in ['rank', 'ranking', 'position', 'this_week', 'thisWeek']:
                                        if rank_key in item:
                                            try:
                                                rank = int(item[rank_key])
                                                break
                                            except:
                                                pass

                                    for name_key in ['name', 'player_name', 'playerName', 'player', 'fullName', 'full_name']:
                                        if name_key in item:
                                            name = item[name_key]
                                            if isinstance(name, dict):
                                                # Sometimes name is nested
                                                name = name.get('full', name.get('display', ''))
                                            break

                                    if rank and name:
                                        rankings[name] = rank

                                if rankings:
                                    print(f"  [OK] Successfully parsed {len(rankings)} rankings!")
                                    return rankings

                        except json.JSONDecodeError:
                            pass

            except Exception as e:
                pass

        time.sleep(1)

    print("  [X] No working API endpoint found")
    return rankings


def scrape_owgr_with_selenium():
    """
    Use Selenium to scrape JavaScript-rendered OWGR rankings
    Requires: pip install selenium webdriver-manager
    """

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("Install with: pip install selenium webdriver-manager")
        return {}

    print("Using Selenium to scrape OWGR...")
    print()

    rankings = {}

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    try:
        # Use webdriver-manager to automatically download and manage Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get('https://www.owgr.com/ranking')

        # Wait for table to load
        print("Waiting for page to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        # Wait longer for JavaScript to populate the table
        print("Waiting for JavaScript to populate data...")
        time.sleep(8)

        # Try to click "show all" or increase page size if there's a dropdown
        try:
            # Look for dropdown or pagination controls
            select_elements = driver.find_elements(By.TAG_NAME, "select")
            for select in select_elements:
                options = select.find_elements(By.TAG_NAME, "option")
                for option in options:
                    if "200" in option.text or "All" in option.text:
                        option.click()
                        time.sleep(3)
                        break
        except:
            pass

        # Save page source for debugging
        with open('owgr_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Saved page source to owgr_page_source.html for debugging")
        print()

        # Try to find data in page source directly using regex
        page_source = driver.page_source
        # Look for patterns like: "name":"Scottie Scheffler","rank":1
        import json
        rank_pattern = r'"rank[Ii]ng?"\s*:\s*(\d+)'
        name_pattern = r'"(?:name|player[Nn]ame|fullName)"\s*:\s*"([^"]+)"'

        rank_matches = re.findall(rank_pattern, page_source)
        name_matches = re.findall(name_pattern, page_source)

        if rank_matches and name_matches and len(rank_matches) == len(name_matches):
            print(f"Found {len(rank_matches)} rankings in page source via regex!")
            for i in range(min(len(rank_matches), len(name_matches))):
                name = name_matches[i]
                rank = int(rank_matches[i])
                if name and rank > 0:
                    rankings[name] = rank
            if rankings:
                return rankings

        # Get table rows
        rows = driver.find_elements(By.TAG_NAME, "tr")

        print(f"Found {len(rows)} table rows")
        print()

        # Debug: look at first few rows
        print("Debugging first 3 rows:")
        for i, row in enumerate(rows[:3]):
            cells = row.find_elements(By.TAG_NAME, "td")
            print(f"  Row {i}: {len(cells)} cells")
            if cells:
                for j, cell in enumerate(cells[:8]):
                    print(f"    Cell {j}: {cell.text[:50] if cell.text else '(empty)'}")
        print()

        # Try different column indices
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")

                if len(cells) >= 3:
                    # Try different combinations
                    for rank_idx in [0, 1]:
                        for name_idx in [1, 2, 3, 4]:
                            try:
                                rank_text = cells[rank_idx].text.strip()
                                name_text = cells[name_idx].text.strip()

                                rank = int(rank_text)
                                if name_text and len(name_text) > 3 and rank > 0:
                                    if name_text not in rankings:
                                        rankings[name_text] = rank
                                    break
                            except:
                                continue

            except Exception as e:
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

    print()
    print(f"[OK] Saved {updated} rankings to database")
    print(f"  Last updated: {timestamp}")


if __name__ == "__main__":
    print("=" * 80)
    print("OWGR RANKINGS SCRAPER")
    print("=" * 80)
    print()

    # Try API approach first
    rankings = fetch_owgr_via_api(page_size=200, max_pages=3)

    # If API doesn't work, try Selenium
    if not rankings:
        print()
        print("=" * 80)
        print("Trying Selenium approach...")
        print("=" * 80)
        print()
        rankings = scrape_owgr_with_selenium()

    if rankings:
        print()
        print(f"Successfully scraped {len(rankings)} players")
        print()

        print("Top 10 ranked players:")
        sorted_rankings = sorted(rankings.items(), key=lambda x: x[1])
        for player, rank in sorted_rankings[:10]:
            print(f"  #{rank}: {player}")

        print()
        print("Checking for Matthieu Pavon...")
        if "Matthieu Pavon" in rankings:
            print(f"  [OK] Found: #{rankings['Matthieu Pavon']}")
        else:
            print("  [X] Not found")

        save_owgr_to_database(rankings)

    else:
        print()
        print("Failed to scrape OWGR rankings")
        print()
        print("Please install Selenium: pip install selenium")
        print("And Chrome WebDriver: https://chromedriver.chromium.org/")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
