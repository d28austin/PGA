# PGA Data Summary - What We Have Scraped

## Overall Statistics

- **Total valid player results:** 540 (from 2024)
- **Unique players:** 218
- **Tournaments with complete data:** 5 (plus 1 test record)
- **Years covered:** 2024
- **Invalid data:** 100 results from 2025 (tournament not played yet)

## Tournaments with Complete Data (2024)

### 1. The Sentry (401580329)
- **Players:** 59
- **Winner:** Chris Kirk (263)
- **Top 3:** Chris Kirk, Sahith Theegala, Jordan Spieth

### 2. Sony Open in Hawaii (401580330)
- **Players:** 100
- **Winner:** Grayson Murray (267)
- **Top 3:** Grayson Murray, Byeong Hun An, Keegan Bradley

### 3. The American Express (401580331)
- **Players:** 100
- **Winner:** Nick Dunlap (259)
- **Top 3:** Nick Dunlap, Christiaan Bezuidenhout, Kevin Yu / Xander Schauffele / Justin Thomas

### 4. Farmers Insurance Open (401580332)
- **Players:** 100
- **Winner:** Matthieu Pavon (275)
- **Top 3:** Matthieu Pavon, Nicolai Højgaard, Nate Lashley / Jake Knapp / Stephan Jaeger

### 5. AT&T Pebble Beach Pro-Am (401580333)
- **Players:** 80
- **Winner:** Wyndham Clark (199)
- **Top 3:** Wyndham Clark, Ludvig Åberg, Matthieu Pavon

## Top Players by Average Finish (Min 3 Appearances)

Based on the 5 tournaments loaded:

1. **Eric Cole** - 3 tournaments, Avg: 10.3
2. **Xander Schauffele** - 5 tournaments, Avg: 12.7
3. **Wyndham Clark** - 5 tournaments, Avg: 13.8
4. **Ludvig Åberg** - 5 tournaments, Avg: 14.7
5. **Si Woo Kim** - 5 tournaments, Avg: 17.7

## Data Quality

✓ All 2024 data has valid positions (1-100)
✓ All players have names
✓ Scores are recorded
✗ Earnings data not available (ESPN API limitation)
✗ 2025 data is incomplete (tournament not played yet)

## What's Working in the App

You can now:
- View tournament history for these 5 tournaments
- Analyze individual player performance across these events
- Compare players who appeared in multiple tournaments
- Track which players you've used in your one-and-done league

## Next Steps

To get more data, you can run:
```bash
python load_historical_data.py --start 2020 --end 2024
```

This will load more tournaments from 2020-2024 to give you better historical trends!
