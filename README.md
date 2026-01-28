# PGA Tour Analysis App

A comprehensive PGA Tour analysis tool built with Streamlit for tournament analysis, player tracking, and one-and-done pool management.

## Features

- **In the Field**: View players in upcoming tournaments with detailed stats and quick analysis
- **Tournament History**: Analyze historical performance at specific tournaments
- **Player Deep Dive**: Detailed player statistics and performance analysis
- **Recent Form**: Track player recent performance trends
- **Compare Players**: Side-by-side player comparisons
- **2026 Schedule**: Full PGA Tour schedule with dates
- **All Players**: Search and manage all players, mark as used for one-and-done pools

## Live App

Access the live app at: [Your Streamlit URL will go here]

## Local Installation

1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/PGA.git
cd PGA
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the app
```bash
streamlit run app.py
```

## Data Sources

- ESPN API for tournament data and player information
- PGA Tour official statistics

## One-and-Done Pool Tracking

The app includes a one-and-done pool tracker that allows you to:
- Mark players as used
- Track which players are still available
- Search and filter players
- Export data to CSV

## Technologies

- **Streamlit**: Web framework
- **Pandas**: Data manipulation
- **SQLite**: Local database for caching
- **Requests**: API calls
- **BeautifulSoup**: Web scraping (when needed)
