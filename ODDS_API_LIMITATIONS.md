# PGA Tournament Odds - API Limitations & Solutions

## 📊 Current Status

### ✅ What Works (Live API Data)
The Odds API provides **live odds** for the 4 major championships:

1. **Masters Tournament** - April
2. **PGA Championship** - May
3. **U.S. Open** - June
4. **The Open Championship** - July

For these tournaments, you get:
- Real-time odds from 4+ bookmakers (DraftKings, FanDuel, BetMGM, Caesars)
- 100+ players with odds
- Updated throughout the week
- **1 API request per load**

### ❌ What Doesn't Work (Regular PGA Tour Events)
The Odds API does **NOT** provide odds for regular tour events like:
- WM Phoenix Open
- Pebble Beach Pro-Am
- Arnold Palmer Invitational
- THE PLAYERS Championship
- Memorial Tournament
- And all other non-major tournaments

## 🔄 Current Solution: Sample Data

For regular tour events (like Phoenix Open), the app uses **curated sample data** that:
- Reflects typical market odds for popular tournaments
- Includes 15-20 top players
- Shows realistic spread from favorites to long shots
- Gets updated as we add more tournaments

### WM Phoenix Open Sample Odds (Current):
```
Scottie Scheffler  +675  (12.9% implied)
Xander Schauffele  +925  (9.8% implied)
Hideki Matsuyama   +1150 (8.0% implied)
Patrick Cantlay    +1350 (6.9% implied)
Collin Morikawa    +1550 (6.1% implied)
```

## 🎯 How to Use Right Now

### For Major Championships (Live Odds):
1. Select: Masters, PGA Championship, US Open, or The Open
2. Go to "🎯 Recommendations" tab
3. Your API key is automatically detected
4. Toggle "Use Live Odds" ON
5. Get real-time data from multiple bookmakers

### For Regular Tour Events (Sample Data):
1. Select: Any regular PGA Tour tournament
2. Go to "🎯 Recommendations" tab
3. System automatically uses sample data
4. You'll see a message: "Using sample WM Phoenix Open odds"
5. Value analysis still works based on historical performance

**Note**: Sample odds are for demonstration purposes. For actual betting, check sportsbook websites directly.

## 🚀 Future Solutions

### Option 1: Premium Odds APIs (Paid)
Services that offer regular PGA Tour odds:
- **OddsJam** ($50-200/month) - All tour events
- **BetQL** ($30-100/month) - Comprehensive coverage
- **RapidAPI Sports Odds** ($10-50/month) - Various providers

### Option 2: Web Scraping (Free but Fragile)
Scrape from sportsbook websites:
- **Pros**: Free, comprehensive
- **Cons**:
  - Violates terms of service
  - Breaks when sites change
  - May get IP blocked
  - Legal gray area

### Option 3: Manual Input (Most Reliable)
Add manual odds entry feature:
- Input odds from your preferred sportsbook
- Store for current tournament
- Best for serious bettors
- Always accurate and legal

### Option 4: Community Database
Create a shared database where users can:
- Submit current odds they see
- App shows average of recent submissions
- Community-verified data
- Requires moderation

## 📝 Recommended Approach

**For Now (Free Tier)**:
1. Use live odds for the 4 majors
2. Use sample data for regular events
3. Manually check DraftKings/FanDuel for actual odds
4. Focus on value analysis (historical performance vs course)

**If You Bet Regularly**:
1. Subscribe to OddsJam or BetQL (~$50/month)
2. They provide APIs for all PGA Tour events
3. Integrate with our app
4. Get complete coverage year-round

**Best Value Approach**:
Even without live odds for every tournament:
- Historical performance analysis is still incredibly valuable
- Course fit and recent form matter most
- Odds are just one data point
- The value methodology works with or without live odds

## 🔧 How Sample Data is Generated

Sample odds are based on:
1. **Player Rankings**: Current OWGR and form
2. **Historical Performance**: Past results at tournament
3. **Market Patterns**: Typical odds spreads
4. **Bookmaker Comparisons**: Realistic variance between books

Updated regularly to reflect:
- Current top players
- Tournament-specific favorites
- Typical market pricing

## ⚠️ Important Disclaimer

**Sample odds are for educational/demonstration purposes only.**

For actual betting:
- Check live odds on sportsbook websites
- DraftKings: https://sportsbook.draftkings.com/
- FanDuel: https://sportsbook.fanduel.com/
- BetMGM: https://sports.betmgm.com/

Never bet based solely on sample data.

## 🎓 What You Still Get

Even without live odds for every tournament, you still get:
- ✅ Comprehensive historical analysis
- ✅ Value scores based on performance
- ✅ Course fit analysis
- ✅ Recent form tracking
- ✅ Top 10 recommendations
- ✅ Player deep dives
- ✅ One-and-done tracking

**The historical analysis is often more valuable than the odds anyway!**

## 📞 Want to Help?

If you have access to a premium odds API or want to contribute to expanding coverage, please reach out!

---

**Current API Usage**: 496 / 500 requests remaining (resets monthly)
**Major Championships**: Full live coverage ✅
**Regular Tour Events**: Sample data (work in progress) 🔄
