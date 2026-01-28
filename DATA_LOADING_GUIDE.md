# PGA Data Loading Guide

## Overview

The app now uses **ESPN PGA API** to fetch tournament data. The PGA Tour official API was not accessible from your network, but ESPN's API works perfectly and provides all the data we need.

## Quick Start - Sample Data (Already Loaded!)

✅ **You already have sample data loaded!**

The system has loaded 5 tournaments from 2024 with 439 player results:
- The Sentry (59 players)
- Sony Open in Hawaii (100 players)
- The American Express (100 players)
- Farmers Insurance Open (100 players)
- AT&T Pebble Beach Pro-Am (80 players)

**You can now run the app and see real data!**

```bash
python -m streamlit run app.py
```

## Loading Historical Data (2000-2025)

To load full historical data for all tournaments from 2000-2025, run:

```bash
python load_historical_data.py --start 2000 --end 2025
```

**⚠️ This will take several hours** due to API rate limiting (we respect ESPN's servers).

### Load Specific Years

Load just recent years (faster):
```bash
python load_historical_data.py --start 2020 --end 2025
```

Load a single year:
```bash
python load_historical_data.py --year 2023
```

### Recommended Approach

1. **Start with the app now** - Use the sample data already loaded
2. **Run overnight load** - Let the historical loader run overnight:
   ```bash
   python load_historical_data.py --start 2015 --end 2025
   ```
3. **Incremental loading** - The script skips tournaments already in the database, so you can run it multiple times

## How the Data Loading Works

### ESPN API Structure

The system fetches:
1. **Tournament Calendar** - List of all tournaments for each year
2. **Competition Data** - For each tournament, gets all competitors
3. **Player Details** - For each player, fetches:
   - Player name and ID
   - Finish position
   - Total score
   - Tournament-specific stats

### Data Storage

All data is stored in: `data/cache/pga_data.db` (SQLite database)

Tables:
- `tournaments` - Tournament info (name, date, course)
- `tournament_results` - Player results (position, score, earnings)
- `used_players` - Your one-and-done picks

### 2026 Current Season Data

The app automatically fetches the current 2026 season schedule when you click "Refresh Tournament Data" in the sidebar. Only current tournament data needs to be refreshed regularly.

## Data Limitations

- **Earnings**: ESPN API doesn't provide earnings data directly (shows as None)
- **Historical Coverage**: ESPN has data going back to ~2015 reliably
- **Rate Limiting**: The loader includes delays to respect API limits

## Troubleshooting

**No data showing in app?**
- Make sure you've run `quick_load_sample_data.py` or `load_historical_data.py`
- Check that `data/cache/pga_data.db` exists

**Loader stopping midway?**
- The script is safe to re-run - it skips already-loaded tournaments
- Just run it again to continue where it left off

**Want to reload a tournament?**
- Delete the database file and re-run the loader
- Or manually delete specific tournament results from the database

## Performance Tips

1. **Load in batches** - Load 5-year chunks instead of all at once
2. **Run overnight** - The full historical load can take 4-6 hours
3. **Use sample data** - For testing, the 5 sample tournaments are sufficient

## Next Steps

1. ✅ Sample data is loaded
2. Run the app: `python -m streamlit run app.py`
3. Test with the 2024 tournaments
4. Start overnight historical load if you want more data
5. Enjoy your one-and-done analyzer!
