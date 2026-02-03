# Weekly Odds Scraping Guide

## Quick Start

Run this **once per week** (Monday or Tuesday before tournament starts):

```bash
cd "C:\Users\Austin.Wheeler\OneDrive - bpx\Documents\VS Code\PGA"
python scrape_weekly_odds.py
```

## What It Does

1. **Opens Chrome** (visible, not headless)
2. **Navigates to DraftKings** golf odds page
3. **Waits for you** to solve any CAPTCHA if needed
4. **Scrolls and loads** all player odds
5. **Scrapes data** from the page
6. **Saves to**:
   - CSV file (`pga_odds_YYYYMMDD_HHMMSS.csv`)
   - Database (`weekly_odds` table)
7. **Closes browser** automatically

## How to Use

### Step 1: Run the Scraper (Once Per Week)

```bash
python scrape_weekly_odds.py
```

**What you'll see:**
```
============================================================
WEEKLY PGA ODDS SCRAPER
============================================================

This will open Chrome and scrape DraftKings odds.
If you see a CAPTCHA, solve it manually.
For personal weekly use only.

Press Enter to start...
```

### Step 2: Solve CAPTCHA (If Needed)

- Chrome will open and load DraftKings
- If you see a CAPTCHA, solve it manually
- Wait 10 seconds for page to fully load
- Script will automatically scrape once ready

### Step 3: View Results

The script shows you what it found:

```
Top 10 Favorites:
  Scottie Scheffler       +700  (12.5%)
  Xander Schauffele       +900  (10.0%)
  Hideki Matsuyama        +1200 ( 7.7%)
  ...

[SAVED] Odds saved to: pga_odds_20260203_143052.csv
[SAVED] Odds saved to database
```

### Step 4: Use in App

The app automatically uses scraped odds when available:

1. **Run your app**: `streamlit run app.py`
2. **Select tournament**
3. **Go to Recommendations tab**
4. **See message**: "Found 87 scraped odds from database"

## Automation (Optional)

### Windows Task Scheduler

Run automatically every Monday:

1. Open **Task Scheduler**
2. Create new **Basic Task**
3. **Trigger**: Weekly, Monday 10 AM
4. **Action**: Start a program
5. **Program**: `python`
6. **Arguments**: `C:\Users\Austin.Wheeler\OneDrive - bpx\Documents\VS Code\PGA\scrape_weekly_odds.py`

**Note**: This only works if DraftKings doesn't show CAPTCHA. You may need to run manually.

## Troubleshooting

### Chrome doesn't open

**Solution**: Install Chrome if not already installed, or update it

```bash
pip install --upgrade selenium webdriver-manager
```

### CAPTCHA every time

**Solution**: This is normal. Solve it manually (takes 5 seconds)

DraftKings shows CAPTCHAs for:
- New IP addresses
- VPN usage
- First visit of the day

### No odds found

**Possible causes:**
1. Page structure changed (DraftKings updates their site)
2. Didn't wait long enough for page load
3. CAPTCHA wasn't solved

**Solution**: Run the script again, wait longer for page load

### "Element not found" errors

**Solution**: DraftKings changed their HTML. Update the scraper:

The scraper looks for these CSS classes:
- `.sportsbook-outcome-cell` - Player container
- `.sportsbook-outcome-cell__label` - Player name
- `.sportsbook-odds` - Odds value

If these change, the scraper needs updating.

## Data Storage

### CSV Files
Located in project root:
- `pga_odds_20260203_143052.csv`
- One file per scraping session
- Keep for your records

### Database
Table: `weekly_odds`

Columns:
- `player_name` - Player name
- `odds` - American odds (+700, -110, etc.)
- `bookmaker` - Always "DraftKings"
- `tournament` - Tournament name (auto-detected)
- `scraped_at` - When odds were scraped
- `created_at` - Database timestamp

### View Database Data

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/cache/pga_data.db')
df = pd.read_sql('SELECT * FROM weekly_odds ORDER BY created_at DESC', conn)
print(df)
```

## Best Practices

### ✅ DO:
- Run once per week (Monday/Tuesday)
- Solve CAPTCHAs manually if needed
- Wait for page to fully load (10 seconds)
- Keep Chrome updated

### ❌ DON'T:
- Run multiple times per day
- Automate CAPTCHA solving (violates TOS)
- Use on VPN (causes more CAPTCHAs)
- Share your data publicly

## Frequency Recommendations

**Optimal schedule:**
- **Monday morning**: Scrape when odds first posted
- **Wednesday**: Update if needed (optional)
- **Once per tournament**: Sufficient for analysis

**Why not daily?**
- Odds don't change that much day-to-day
- More scraping = more CAPTCHA challenges
- Weekly is respectful to site
- Still get accurate data for analysis

## Priority vs. Sample Data

The app uses odds in this priority:

1. **Scraped odds from database** (your weekly scraping)
2. **Live API for majors** (Masters, PGA, US Open, The Open)
3. **Sample data** (fallback)

So your scraped odds always take priority!

## Example Workflow

**Monday 10 AM:**
```bash
# Scrape current tournament odds
python scrape_weekly_odds.py
```

**Throughout the week:**
```bash
# Use the app with your scraped odds
streamlit run app.py
```

**Next Monday:**
```bash
# Scrape new tournament odds
python scrape_weekly_odds.py
```

## Future Enhancements

Want to add:
- **FanDuel scraping** (compare multiple books)
- **Top 10 finish odds** (in addition to winner)
- **Head-to-head matchups**

Let me know and I can add these!

## Legal Note

This is for **personal use only**:
- ✅ Once per week for your own analysis
- ✅ Manual CAPTCHA solving
- ✅ Respectful of site resources

**NOT for:**
- ❌ Commercial use
- ❌ Reselling data
- ❌ High-frequency automated scraping
- ❌ Bypassing CAPTCHAs automatically

Use responsibly!
