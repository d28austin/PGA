"""
Weekly PGA Odds Scraper using Selenium
For personal use - run once per week before tournament starts

Usage:
    python scrape_weekly_odds.py

The script will:
1. Open Chrome browser
2. Navigate to DraftKings
3. Wait for you to solve any CAPTCHA if needed
4. Scrape tournament winner odds
5. Save to CSV and database
6. Close browser

For weekly use only - respects site terms by not being automated/high-frequency
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


class WeeklyOddsScraper:
    """Scrape PGA odds once per week using Selenium"""

    def __init__(self, headless=False):
        """
        Initialize scraper

        Args:
            headless: Run browser in background (False = visible for CAPTCHA solving)
        """
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Setup Chrome driver with Selenium"""
        print("Setting up Chrome browser...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        # Make browser look more human
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Install and setup ChromeDriver automatically
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("Browser ready!")

    def scrape_draftkings(self) -> pd.DataFrame:
        """
        Scrape DraftKings PGA tournament winner odds

        Returns:
            DataFrame with player odds
        """
        print("\n" + "="*60)
        print("DRAFTKINGS - Tournament Winner Odds")
        print("="*60)

        try:
            url = "https://sportsbook.draftkings.com/leagues/golf/88670846"
            print(f"Loading: {url}")

            self.driver.get(url)

            # Wait for user if CAPTCHA appears
            print("\nIf you see a CAPTCHA, please solve it now...")
            print("Waiting for page to fully load...")

            # Wait longer and look for specific elements
            try:
                # Wait up to 30 seconds for odds to appear
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "sportsbook-outcome-cell"))
                )
                print("Page loaded - odds elements found!")
            except:
                print("WARNING: Odds elements not found yet, waiting more...")
                time.sleep(10)

            # Give extra time for all odds to render
            time.sleep(5)

            # Try to find tournament name
            try:
                tournament_element = self.driver.find_element(By.CSS_SELECTOR, "h1.event-cell__name, h1, .sportsbook-event-accordion__title")
                tournament_name = tournament_element.text
                print(f"\nTournament: {tournament_name}")
            except:
                tournament_name = "Current PGA Tournament"
                print(f"\nTournament: {tournament_name} (name not found)")

            # Scroll to load all players
            print("Scrolling to load all odds...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            for _ in range(3):  # Scroll 3 times
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Save page source for debugging
            page_source = self.driver.page_source
            try:
                debug_file = f"debug_page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"Page source saved to: {debug_file}")
            except:
                pass

            # Parse odds from page
            odds_list = []

            # Method 1: Try to find odds in page source (JSON data)
            if 'outcomes' in page_source or 'oddsAmerican' in page_source:
                # Try to extract JSON from script tags
                scripts = self.driver.find_elements(By.TAG_NAME, "script")
                for script in scripts:
                    try:
                        script_content = script.get_attribute('innerHTML')
                        if script_content and ('outcomes' in script_content or 'oddsAmerican' in script_content):
                            # Try to parse as JSON
                            try:
                                data = json.loads(script_content)
                                odds_list = self._extract_odds_from_json(data)
                                if odds_list:
                                    break
                            except:
                                pass
                    except:
                        continue

            # Method 2: Parse visible HTML elements
            if not odds_list:
                print("Parsing HTML elements...")
                odds_list = self._parse_dk_html_elements()

            # Method 3: If still nothing, take screenshot and ask user
            if not odds_list:
                print("\n" + "="*60)
                print("Could not find odds automatically.")
                print("The page is still open in Chrome.")
                print("\nDEBUG TIPS:")
                print("1. Look at the Chrome window - do you see odds?")
                print("2. Right-click on a player name -> Inspect")
                print("3. Note the class names used")
                print("="*60)

                # Take screenshot for debugging
                try:
                    screenshot_path = f"debug_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"\nScreenshot saved to: {screenshot_path}")
                except:
                    pass

                user_input = input("\nWould you like to try manual extraction? (y/n): ")
                if user_input.lower() == 'y':
                    odds_list = self._manual_extraction_prompt()

            if odds_list:
                df = pd.DataFrame(odds_list)
                df['tournament'] = tournament_name
                df['scraped_at'] = datetime.now().isoformat()
                print(f"\n[SUCCESS] Found {len(df)} player odds!")
                return df
            else:
                print("\n[WARNING] No odds found - page may have changed")
                return pd.DataFrame()

        except Exception as e:
            print(f"\n[ERROR] Scraping failed: {e}")
            return pd.DataFrame()

    def _extract_odds_from_json(self, data, odds_list=None, depth=0):
        """Recursively extract odds from JSON data"""
        if odds_list is None:
            odds_list = []

        if depth > 15:
            return odds_list

        if isinstance(data, dict):
            # Look for outcomes array
            if 'outcomes' in data and isinstance(data['outcomes'], list):
                for outcome in data['outcomes']:
                    if isinstance(outcome, dict):
                        player = outcome.get('label', outcome.get('name', ''))
                        odds = outcome.get('oddsAmerican', outcome.get('odds', None))

                        if player and odds:
                            try:
                                # Clean player name
                                player = player.strip()
                                # Convert odds to int
                                if isinstance(odds, str):
                                    odds = int(odds.replace('+', '').replace('−', '-'))
                                else:
                                    odds = int(odds)

                                odds_list.append({
                                    'player_name': player,
                                    'odds': odds,
                                    'bookmaker': 'DraftKings'
                                })
                            except:
                                pass

            # Recurse through all values
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._extract_odds_from_json(value, odds_list, depth + 1)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_odds_from_json(item, odds_list, depth + 1)

        return odds_list

    def _parse_dk_html_elements(self):
        """Parse DraftKings HTML for visible odds"""
        odds_list = []

        print("\nAttempting to parse HTML elements...")

        # Try multiple selector strategies
        strategies = [
            {
                'name': 'Strategy 1: sportsbook-outcome-cell',
                'container': 'sportsbook-outcome-cell',
                'name_selector': 'sportsbook-outcome-cell__label',
                'odds_selector': 'sportsbook-odds'
            },
            {
                'name': 'Strategy 2: outcome-cell variations',
                'container': 'outcome-cell',
                'name_selector': 'outcome-cell__label',
                'odds_selector': 'outcome-cell__odds'
            },
            {
                'name': 'Strategy 3: Generic approach',
                'container': None,  # Will use different approach
                'name_selector': None,
                'odds_selector': None
            }
        ]

        for strategy in strategies:
            print(f"\nTrying {strategy['name']}...")

            if strategy['container']:
                try:
                    # Find all outcome cells
                    outcome_cells = self.driver.find_elements(By.CLASS_NAME, strategy['container'])
                    print(f"  Found {len(outcome_cells)} outcome cells")

                    if len(outcome_cells) > 0:
                        for i, cell in enumerate(outcome_cells):
                            try:
                                # Get player name - try multiple methods
                                player_name = None
                                try:
                                    player_element = cell.find_element(By.CLASS_NAME, strategy['name_selector'])
                                    player_name = player_element.text.strip()
                                except:
                                    # Try aria-label or other attributes
                                    try:
                                        player_name = cell.get_attribute('aria-label')
                                    except:
                                        pass

                                # Get odds - try multiple methods
                                odds_text = None
                                try:
                                    odds_element = cell.find_element(By.CLASS_NAME, strategy['odds_selector'])
                                    odds_text = odds_element.text.strip()
                                except:
                                    # Try getting from button text or other elements
                                    try:
                                        button = cell.find_element(By.TAG_NAME, 'button')
                                        odds_text = button.text.strip()
                                    except:
                                        pass

                                if player_name and odds_text:
                                    # Parse odds
                                    # Remove non-numeric characters except + and -
                                    import re
                                    odds_match = re.search(r'([+\-]?\d+)', odds_text)
                                    if odds_match:
                                        odds = int(odds_match.group(1))

                                        odds_list.append({
                                            'player_name': player_name,
                                            'odds': odds,
                                            'bookmaker': 'DraftKings'
                                        })

                                        if i < 3:  # Show first 3 for debugging
                                            print(f"    Found: {player_name} = {odds:+d}")

                            except Exception as e:
                                continue

                        if odds_list:
                            print(f"  SUCCESS! Found {len(odds_list)} odds")
                            return odds_list

                except Exception as e:
                    print(f"  Failed: {e}")
                    continue
            else:
                # Strategy 3: Generic approach - find all elements with odds-like text
                print("  Trying generic text search...")
                try:
                    # Get all text from page
                    all_text = self.driver.find_element(By.TAG_NAME, 'body').text

                    # Look for patterns like "Player Name +700"
                    import re
                    # Pattern: any text followed by American odds
                    pattern = r'([A-Z][a-zA-Z\s\.]+?)\s+([+\-]\d{3,5})'
                    matches = re.findall(pattern, all_text)

                    for player, odds_str in matches:
                        player = player.strip()
                        try:
                            odds = int(odds_str)
                            odds_list.append({
                                'player_name': player,
                                'odds': odds,
                                'bookmaker': 'DraftKings'
                            })
                        except:
                            continue

                    if odds_list:
                        # Remove duplicates
                        seen = set()
                        unique_odds = []
                        for item in odds_list:
                            key = item['player_name']
                            if key not in seen:
                                seen.add(key)
                                unique_odds.append(item)

                        print(f"  Found {len(unique_odds)} unique odds via text search")
                        return unique_odds

                except Exception as e:
                    print(f"  Failed: {e}")

        print("\nAll strategies failed")
        return odds_list

    def _manual_extraction_prompt(self):
        """Prompt user to manually provide class names from inspection"""
        print("\n" + "="*60)
        print("MANUAL EXTRACTION MODE")
        print("="*60)
        print("\nInstructions:")
        print("1. In Chrome, right-click on a player's name")
        print("2. Select 'Inspect' or 'Inspect Element'")
        print("3. Look for the class name (e.g., 'player-name-v2' or 'outcome-label')")
        print("4. Do the same for the odds number")
        print()

        player_class = input("Enter the class name for PLAYER NAME (or press Enter to skip): ").strip()
        odds_class = input("Enter the class name for ODDS NUMBER (or press Enter to skip): ").strip()

        if player_class and odds_class:
            print("\nAttempting extraction with your class names...")
            try:
                odds_list = []
                players = self.driver.find_elements(By.CLASS_NAME, player_class)
                odds_elements = self.driver.find_elements(By.CLASS_NAME, odds_class)

                print(f"Found {len(players)} players and {len(odds_elements)} odds elements")

                for player, odds_elem in zip(players, odds_elements):
                    try:
                        player_name = player.text.strip()
                        odds_text = odds_elem.text.strip()

                        import re
                        odds_match = re.search(r'([+\-]?\d+)', odds_text)
                        if odds_match and player_name:
                            odds = int(odds_match.group(1))
                            odds_list.append({
                                'player_name': player_name,
                                'odds': odds,
                                'bookmaker': 'DraftKings'
                            })
                    except:
                        continue

                if odds_list:
                    print(f"SUCCESS! Extracted {len(odds_list)} odds")
                    return odds_list

            except Exception as e:
                print(f"Manual extraction failed: {e}")

        return []

    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """Save odds to CSV file"""
        if df.empty:
            print("No data to save")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pga_odds_{timestamp}.csv"

        df.to_csv(filename, index=False)
        print(f"\n[SAVED] Odds saved to: {filename}")

    def save_to_database(self, df: pd.DataFrame, db_path: str = "data/cache/pga_data.db"):
        """Save odds to database"""
        if df.empty:
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create odds table if doesn't exist
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

            # Clear old odds for this tournament
            if 'tournament' in df.columns:
                tournament = df['tournament'].iloc[0]
                cursor.execute("DELETE FROM weekly_odds WHERE tournament = ?", (tournament,))

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
            print(f"[SAVED] Odds saved to database")

        except Exception as e:
            print(f"[ERROR] Database save failed: {e}")

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("\nBrowser closed")


def main():
    """Main function to run weekly scraping"""
    print("\n" + "="*60)
    print("WEEKLY PGA ODDS SCRAPER")
    print("="*60)
    print("\nThis will open Chrome and scrape DraftKings odds.")
    print("If you see a CAPTCHA, solve it manually.")
    print("For personal weekly use only.\n")

    input("Press Enter to start...")

    scraper = WeeklyOddsScraper(headless=False)  # Visible browser for CAPTCHA solving

    try:
        # Setup browser
        scraper.setup_driver()

        # Scrape DraftKings
        dk_odds = scraper.scrape_draftkings()

        if not dk_odds.empty:
            # Show results
            print("\n" + "="*60)
            print("ODDS SUMMARY")
            print("="*60)

            top_10 = dk_odds.nsmallest(10, 'odds')
            print("\nTop 10 Favorites:")
            for i, row in top_10.iterrows():
                prob = 100 / (row['odds'] + 100) if row['odds'] > 0 else abs(row['odds']) / (abs(row['odds']) + 100)
                print(f"  {row['player_name']:30s} {row['odds']:+5d} ({prob*100:4.1f}%)")

            # Save to files
            scraper.save_to_csv(dk_odds)
            scraper.save_to_database(dk_odds)

            print("\n" + "="*60)
            print("[COMPLETE] Odds scraped successfully!")
            print("="*60)
        else:
            print("\n[FAILED] Could not scrape odds")

    except Exception as e:
        print(f"\n[ERROR] {e}")

    finally:
        # Close browser
        scraper.close()

    print("\nDone! Run this again next week.")


if __name__ == "__main__":
    main()
