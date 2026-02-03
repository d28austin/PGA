# Scraper Debugging Guide

## If Scraper Doesn't Find Odds

The scraper tries multiple strategies but DraftKings changes their HTML frequently. Here's how to fix it:

### Quick Fix (5 minutes)

#### Step 1: Run the Scraper
```bash
python scrape_weekly_odds.py
```

#### Step 2: When It Fails
You'll see:
```
Could not find odds automatically.
The page is still open in Chrome.

Would you like to try manual extraction? (y/n):
```

Type **y** and press Enter

#### Step 3: Inspect the Page
In the Chrome window that's still open:

1. **Right-click on a player's name** (e.g., "Scottie Scheffler")
2. Select **"Inspect"** or **"Inspect Element"**
3. Look for the class name in the HTML:
   ```html
   <div class="outcome-name-v3">Scottie Scheffler</div>
   ```
   The class is: **outcome-name-v3**

4. **Right-click on the odds** (e.g., "+700")
5. Select **"Inspect"**
6. Look for the class name:
   ```html
   <span class="odds-display-v2">+700</span>
   ```
   The class is: **odds-display-v2**

#### Step 4: Enter Class Names
When prompted:
```
Enter the class name for PLAYER NAME: outcome-name-v3
Enter the class name for ODDS NUMBER: odds-display-v2
```

The scraper will re-run with your class names!

### Example HTML Structures

DraftKings uses different structures. Here are common ones:

**Version 1 (2024):**
```html
<div class="sportsbook-outcome-cell">
  <span class="sportsbook-outcome-cell__label">Scottie Scheffler</span>
  <span class="sportsbook-odds">+700</span>
</div>
```

**Version 2 (2025):**
```html
<div class="outcome-cell-v2">
  <div class="outcome-name">Scottie Scheffler</div>
  <div class="outcome-odds">+700</div>
</div>
```

**Version 3 (Possible future):**
```html
<button class="player-odds-btn">
  <span class="player-name-text">Scottie Scheffler</span>
  <span class="american-odds">+700</span>
</button>
```

### Debug Files

The scraper automatically saves these when it fails:

1. **`debug_screenshot_YYYYMMDD_HHMMSS.png`**
   - Screenshot of the page
   - Shows exactly what the browser sees

2. **`debug_page_source_YYYYMMDD_HHMMSS.html`**
   - Full HTML source code
   - Search for player names to find the right structure

### Permanent Fix (Update the Scraper)

If you want to update the scraper permanently:

1. Open `scrape_weekly_odds.py`

2. Find the `_parse_dk_html_elements` method

3. Add your strategy at the top:
   ```python
   strategies = [
       {
           'name': 'Strategy 1: Your version',
           'container': 'outcome-cell-v2',  # Your container class
           'name_selector': 'outcome-name',  # Your name class
           'odds_selector': 'outcome-odds'   # Your odds class
       },
       # ... existing strategies ...
   ]
   ```

4. Save and run again

### Common Issues

#### Issue: "Found 0 outcome cells"
**Cause**: Class names changed

**Solution**: Use manual extraction (see above)

#### Issue: "Found 87 outcome cells" but no odds
**Cause**: Odds are in a different element

**Solution**:
1. Inspect the odds number specifically
2. Look for its class name
3. Update the scraper

#### Issue: Only getting partial data (like 10 players instead of 87)
**Cause**: Need to scroll more or wait longer

**Solution**: Update the scroll section:
```python
for _ in range(5):  # Increased from 3 to 5
    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Increased wait
```

#### Issue: Page won't load at all
**Cause**: CAPTCHA or connection issue

**Solution**:
1. Solve any CAPTCHA manually
2. Wait 30 seconds for page to fully load
3. Check your internet connection

### Advanced: Finding Class Names Programmatically

If you want to analyze the page source file:

```python
import re

# Read the debug HTML file
with open('debug_page_source_20260203_143052.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all class names
classes = re.findall(r'class="([^"]+)"', html)

# Find classes that might be player names (usually longer text)
for cls in set(classes):
    if 'outcome' in cls or 'player' in cls or 'name' in cls:
        print(f"Potential name class: {cls}")

# Find classes that might be odds
for cls in set(classes):
    if 'odd' in cls or 'price' in cls or 'line' in cls:
        print(f"Potential odds class: {cls}")
```

### Still Not Working?

Send me:
1. The debug screenshot
2. The debug HTML file (first 500 lines)
3. What you see manually in Chrome

I'll update the scraper with the correct selectors!

## Strategy 3 Explanation (Regex Text Search)

If HTML parsing fails, the scraper tries a "brute force" approach:

1. Gets ALL text from the page
2. Looks for patterns like:
   ```
   Scottie Scheffler +700
   Xander Schauffele +900
   ```
3. Extracts player names and odds using regex

This works if:
- ✅ Odds are visible as text on the page
- ✅ Format is "Name +Number" or "Name -Number"

This doesn't work if:
- ❌ Odds are in images
- ❌ Odds are loaded later
- ❌ Format is completely different

## Testing Your Changes

After making changes, test with a dry run:

```python
from scrape_weekly_odds import WeeklyOddsScraper

scraper = WeeklyOddsScraper()
scraper.setup_driver()

# Navigate to page
scraper.driver.get("https://sportsbook.draftkings.com/leagues/golf/88670846")
input("Press Enter after page loads...")

# Test parsing
odds = scraper._parse_dk_html_elements()
print(f"Found {len(odds)} odds")

# Test first few
for odd in odds[:5]:
    print(f"{odd['player_name']}: {odd['odds']}")

scraper.close()
```

This lets you test without running the full scraper.
