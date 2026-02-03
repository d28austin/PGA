# Betting Odds Integration Guide

## Overview

The PGA Tour Analysis App now includes live betting odds integration to enhance value calculations and recommendations. This feature combines historical performance data with real-time betting markets to identify undervalued players.

## Features

### 1. Live Betting Odds
- Fetch real-time tournament winner odds
- Top 10 finish odds (when available)
- Multiple bookmaker comparison
- Best odds identification

### 2. Value Analysis
- **Value Score**: Combines historical performance, recent form, and course fit
- **Implied Probability**: What bookmakers think the win chance is
- **Value Edge**: Shows if a player is underpriced by the market
- **Positive Edge**: Good betting value (player's chances > what odds suggest)
- **Negative Edge**: Overpriced (odds suggest better chances than reality)

### 3. Enhanced Recommendations
- Top 10 value picks for each tournament
- Visual breakdowns of value components
- Value vs odds scatter plots
- Export recommendations to CSV

## Getting Started

### Option 1: Use Sample Data (No Setup Required)
The app includes sample betting odds data for testing and demonstration purposes.

1. Navigate to the "🎯 Recommendations" tab
2. Check "Use Sample Odds Data"
3. View value analysis with sample odds

### Option 2: Live Odds with The Odds API

#### Step 1: Get a Free API Key

1. Go to: https://the-odds-api.com/
2. Click "Get Started Free"
3. Sign up with your email
4. Free tier includes:
   - 500 requests per month
   - Access to 20+ bookmakers
   - Tournament winner odds
   - Top finishes markets

#### Step 2: Enter API Key in App

1. Go to the "🎯 Recommendations" tab
2. Enter your API key in the text field
3. The app will automatically fetch live odds

#### Step 3: View Live Odds

- Tournament winner odds from multiple bookmakers
- Best odds across all books
- Implied win probabilities
- Value edges for each player

## Understanding the Metrics

### Value Score (0-100+)
- **70+**: Excellent value - Strong historical performance
- **50-70**: Good value - Solid track record
- **30-50**: Fair value - Average performance
- **<30**: Poor value - Weak historical data

Components:
- **History Score** (0-70): Based on wins and top 10s at this course
- **Form Score** (0-40): Recent performance (last 10 events)
- **Course Fit Score** (0-30): Scoring average vs par

### Value Edge (%)
Shows the edge over bookmaker odds:

```
Value Edge = ((Historical Win Rate - Implied Probability) / Implied Probability) × 100
```

- **+50% or higher**: Significant value - player much better than odds suggest
- **+20% to +50%**: Good value - noticeable edge
- **0% to +20%**: Slight value - small edge
- **Negative**: Overpriced - avoid or bet against

### Examples

**Example 1: Strong Value**
- Player: Scottie Scheffler
- Historical Win Rate: 15% (has won this tournament before)
- Odds: +800 (Implied: 11.1%)
- Value Edge: +35% ✅ GOOD VALUE

**Example 2: Overpriced**
- Player: Popular Player
- Historical Win Rate: 3% (poor track record here)
- Odds: +300 (Implied: 25%)
- Value Edge: -88% ❌ AVOID

## API Usage Tips

### Managing Your API Limits

Free tier: 500 requests/month

**Tips to conserve requests:**
1. Use sample data for exploration
2. Only fetch live odds when making actual picks
3. Cache odds data (the app fetches all players in one request)
4. Consider upgrading if you need more requests

### Bookmakers Included

The Odds API aggregates from 20+ bookmakers including:
- DraftKings
- FanDuel
- BetMGM
- Caesars
- PointsBet
- And many more

## Best Practices

### 1. Look for Multiple Positive Indicators
Don't just rely on value edge. Look for:
- ✅ High value score (60+)
- ✅ Positive value edge (+20% or more)
- ✅ Multiple top 10 finishes at this course
- ✅ Good recent form

### 2. Course History Matters Most
- A player with 5+ events at this course is more reliable
- Recent wins at this venue are the strongest indicator
- Consistent top 10s > one lucky win

### 3. Combine with Other Tabs
- Check "Tournament History" for detailed course record
- Review "Recent Form" for current performance trends
- Use "Player Deep Dive" for comprehensive analysis

### 4. Market Efficiency
Remember that betting markets are generally efficient:
- Large edges might indicate missing information
- Popular players are often overpriced
- Lesser-known players with good history can offer value

## Troubleshooting

### "No odds available"
- Tournament might not have odds yet (typically posted Tuesday/Wednesday)
- Event might not be covered by bookmakers
- Use sample data to test functionality

### API key not working
- Check that you copied the entire key
- Verify your free tier hasn't exceeded 500 requests
- Make sure the key is active on The Odds API dashboard

### Odds seem outdated
- Odds update in real-time when you load the tab
- Each tab load = 1 API request
- Refresh the tab to get latest odds

## Advanced Features (Coming Soon)

- **Top 10/Top 5 Odds**: Enhanced markets beyond just winner
- **Head-to-Head Matchups**: Compare two players directly
- **Line Movement**: Track how odds change over time
- **Arbitrage Detection**: Find guaranteed profit opportunities
- **Historical Odds Analysis**: See how accurate odds have been

## Support

For issues with:
- **The app**: Contact the developer
- **The Odds API**: Visit https://the-odds-api.com/support
- **Betting questions**: Consult responsible gambling resources

---

**Disclaimer**: This tool is for educational and entertainment purposes. Always gamble responsibly and within your means. Past performance does not guarantee future results.
