# Quick Start Guide

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## First Steps

### 1. Load Tournament Schedule
- Click **"Refresh Tournament Data"** in the sidebar
- This loads the current PGA Tour season schedule
- Select a tournament from the dropdown

### 2. Fetch Historical Data
- Go to the **"Tournament History"** tab
- Set your desired year range (e.g., 2019-2024)
- Click **"Fetch Tournament Data for Selected Years"**
- Wait for the data to load (this may take a minute)

### 3. Analyze Players

**Tournament History Tab:**
- View all players and their historical performance
- Sort by average finish to find consistent performers
- Check "Hide already used players" to filter your available options

**Player Deep Dive Tab:**
- Select a specific player from the dropdown
- Review their year-by-year performance
- Look at performance trends and insights
- Mark the player as used when you make your pick

**Compare Players Tab:**
- Select 2-4 players to compare side-by-side
- View their statistics and trends
- Get recommendations based on recent form

## Making Your Pick

1. Analyze players using the various tabs
2. In the Player Deep Dive tab, click **"Mark [Player] as Used"**
3. Or in Tournament History tab, select the player and click **"Mark as Used"**
4. Used players will be marked with 🚫 and can be filtered out

## Tips

- **Start with Tournament History**: Get an overview of all players
- **Deep Dive on Top Performers**: Research 3-4 promising players in detail
- **Compare Your Finalists**: Use the comparison tab to make your final decision
- **Track Your Picks**: Keep the one-and-done tracker updated

## Common Issues

**No data showing?**
- Make sure you clicked "Refresh Tournament Data" first
- Fetch historical data for the tournament you selected

**Player not showing up?**
- They may not have played in this tournament in your selected year range
- Try expanding the year range

**Want to start fresh?**
- Click "Clear All Used Players" to reset your one-and-done tracker
- Delete the `data/cache/pga_data.db` file to clear all cached data

## Next Steps

Once you're comfortable with the basics:
- Experiment with different year ranges to see longer trends
- Use the comparison feature to test different player combinations
- Export comparison data for offline analysis
- Track your picks throughout the season to refine your strategy

Enjoy your one-and-done league!
