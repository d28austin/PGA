"""
FanDuel PGA Odds Scraper using Selenium
Adapted from DraftKings scraper for FanDuel Sportsbook

Usage:
    python scrape_fanduel_odds.py
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
import sqlite3
import json
import re


class FanDuelOddsScraper:
    """Scrape PGA odds from FanDuel using Selenium"""

    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Setup Chrome driver"""
        print("Setting up Chrome browser...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("Browser ready!")

    def scrape_fanduel(self) -> pd.DataFrame:
        """Scrape FanDuel PGA tournament winner odds"""
        print("\n" + "="*60)
        print("FANDUEL - Tournament Winner Odds")
        print("="*60)

        try:
            url = "https://sportsbook.fanduel.com/golf"
            print(f"Loading: {url}")

            self.driver.get(url)

            print("\nIf you see a CAPTCHA or need to accept cookies, please handle it now...")
            print("Waiting for page to load...")

            # Wait for odds to appear
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[role='button'], .odds, button"))
                )
                print("Page loaded!")
            except:
                print("WARNING: Timeout waiting for elements...")

            time.sleep(5)

            # Scroll to load all players
            print("Scrolling to load all odds...")
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Save debug files
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            try:
                with open(f"debug_fanduel_{timestamp}.html", 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"Page source saved to: debug_fanduel_{timestamp}.html")
            except:
                pass

            # Try to find tournament name
            tournament_name = self._get_tournament_name()
            print(f"\nTournament: {tournament_name}")

            # Parse odds
            odds_list = self._parse_fanduel_odds()

            if odds_list:
                df = pd.DataFrame(odds_list)
                df['tournament'] = tournament_name
                df['scraped_at'] = datetime.now().isoformat()
                print(f"\n[SUCCESS] Found {len(df)} player odds!")
                return df
            else:
                print("\n[WARNING] No odds found")
                print("The browser will stay open for 30 seconds for inspection...")
                time.sleep(30)
                return pd.DataFrame()

        except Exception as e:
            print(f"\n[ERROR] {e}")
            return pd.DataFrame()

    def _get_tournament_name(self):
        """Try to find tournament name on page"""
        try:
            # Try common selectors for FanDuel
            selectors = [
                "h1", "h2",
                "[class*='tournament']",
                "[class*='event-name']",
                "[data-testid*='title']"
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text and len(text) > 3:
                        return text
                except:
                    continue
        except:
            pass

        return "Current PGA Tournament"

    def _parse_fanduel_odds(self):
        """Parse FanDuel odds from page"""
        odds_list = []

        print("\nParsing FanDuel odds...")

        # Strategy 1: Look for JSON in page source
        page_source = self.driver.page_source
        odds_list = self._extract_from_json(page_source)

        if odds_list:
            print(f"Found {len(odds_list)} odds via JSON extraction")
            return odds_list

        # Strategy 2: Parse HTML elements
        print("Trying HTML element parsing...")
        odds_list = self._parse_html_elements()

        if odds_list:
            print(f"Found {len(odds_list)} odds via HTML parsing")
            return odds_list

        # Strategy 3: Manual help
        print("\nCould not find odds automatically.")
        print("PLEASE INSPECT THE PAGE:")
        print("1. Right-click on a player name -> Inspect")
        print("2. Note the class name")
        print("3. Do the same for the odds number")

        return []

    def _extract_from_json(self, page_source):
        """Try to extract odds from embedded JSON"""
        odds_list = []

        try:
            # Look for JSON patterns
            scripts = self.driver.find_elements(By.TAG_NAME, "script")

            for script in scripts:
                try:
                    content = script.get_attribute('innerHTML')
                    if not content:
                        continue

                    # Look for odds-like data
                    if 'americanOdds' in content or 'outcome' in content.lower():
                        try:
                            data = json.loads(content)
                            extracted = self._parse_json_odds(data)
                            if extracted:
                                odds_list.extend(extracted)
                        except:
                            pass
                except:
                    continue

        except Exception as e:
            print(f"JSON extraction error: {e}")

        return odds_list

    def _parse_json_odds(self, data, depth=0):
        """Recursively parse JSON for odds data"""
        if depth > 10:
            return []

        odds_list = []

        if isinstance(data, dict):
            # Look for player/odds patterns
            if 'name' in data and 'odds' in str(data):
                player = data.get('name', '')
                odds_val = data.get('americanOdds') or data.get('odds')

                if player and odds_val:
                    try:
                        odds_list.append({
                            'player_name': player,
                            'odds': int(odds_val),
                            'bookmaker': 'FanDuel'
                        })
                    except:
                        pass

            # Recurse
            for value in data.values():
                if isinstance(value, (dict, list)):
                    odds_list.extend(self._parse_json_odds(value, depth + 1))

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    odds_list.extend(self._parse_json_odds(item, depth + 1))

        return odds_list

    def _parse_html_elements(self):
        """Parse visible HTML elements for odds"""
        odds_list = []

        # Try to find all text with odds pattern
        try:
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Pattern: Player Name followed by odds (e.g., "Scottie Scheffler +650")
            pattern = r'([A-Z][a-zA-Z\s\.]+?)\s+([+\-]\d{3,5})'
            matches = re.findall(pattern, body_text)

            for player, odds_str in matches:
                player = player.strip()
                try:
                    odds = int(odds_str)
                    odds_list.append({
                        'player_name': player,
                        'odds': odds,
                        'bookmaker': 'FanDuel'
                    })
                except:
                    continue

            # Remove duplicates
            seen = set()
            unique_odds = []
            for item in odds_list:
                key = item['player_name']
                if key not in seen:
                    seen.add(key)
                    unique_odds.append(item)

            return unique_odds

        except Exception as e:
            print(f"HTML parsing error: {e}")
            return []

    def save_to_database(self, df: pd.DataFrame, db_path: str = "data/cache/pga_data.db"):
        """Save odds to database"""
        if df.empty:
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weekly_odds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    odds INTEGER NOT NULL,
                    bookmaker TEXT NOT NULL,
                    tournament TEXT,
                    scraped_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Clear old FanDuel odds for this tournament
            if 'tournament' in df.columns:
                tournament = df['tournament'].iloc[0]
                cursor.execute(
                    "DELETE FROM weekly_odds WHERE tournament = ? AND bookmaker = 'FanDuel'",
                    (tournament,)
                )

            # Insert new odds
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO weekly_odds (player_name, odds, bookmaker, tournament, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row['player_name'],
                    row['odds'],
                    row['bookmaker'],
                    row.get('tournament', 'Unknown'),
                    row.get('scraped_at', datetime.now().isoformat())
                ))

            conn.commit()
            conn.close()
            print(f"[SAVED] {len(df)} odds saved to database")

        except Exception as e:
            print(f"[ERROR] Database save failed: {e}")

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("\nBrowser closed")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("FANDUEL PGA ODDS SCRAPER")
    print("="*60)
    print("\nOpening Chrome to scrape FanDuel odds...")
    print("Handle any CAPTCHAs or cookie prompts manually.")
    print("Starting in 3 seconds...\n")
    time.sleep(3)

    scraper = FanDuelOddsScraper(headless=False)

    try:
        scraper.setup_driver()
        fd_odds = scraper.scrape_fanduel()

        if not fd_odds.empty:
            print("\n" + "="*60)
            print("ODDS SUMMARY")
            print("="*60)

            top_10 = fd_odds.nsmallest(10, 'odds')
            print("\nTop 10 Favorites:")
            for i, row in top_10.iterrows():
                prob = 100 / (row['odds'] + 100) if row['odds'] > 0 else abs(row['odds']) / (abs(row['odds']) + 100)
                print(f"  {row['player_name']:30s} {row['odds']:+5d} ({prob*100:4.1f}%)")

            # Save
            scraper.save_to_database(fd_odds)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fanduel_odds_{timestamp}.csv"
            fd_odds.to_csv(filename, index=False)
            print(f"\n[SAVED] CSV: {filename}")

            print("\n[COMPLETE] FanDuel odds scraped successfully!")
        else:
            print("\n[FAILED] Could not scrape odds")

    except Exception as e:
        print(f"\n[ERROR] {e}")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
