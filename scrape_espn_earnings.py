"""
Scrape earnings data from ESPN tournament leaderboard API
"""

import requests
import time

def scrape_tournament_earnings(tournament_id):
    """
    Scrape earnings from ESPN leaderboard API

    Args:
        tournament_id: ESPN tournament ID (e.g., '401580329')

    Returns:
        dict: {player_name: earnings_amount}
    """
    # Use ESPN's API endpoint instead of HTML scraping
    url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
    params = {
        'league': 'pga',
        'event': tournament_id
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}

        data = response.json()

        # Navigate to competitors
        if 'events' not in data or len(data['events']) == 0:
            return {}

        event = data['events'][0]

        if 'competitions' not in event or len(event['competitions']) == 0:
            return {}

        competition = event['competitions'][0]

        if 'competitors' not in competition:
            return {}

        competitors = competition['competitors']

        earnings_data = {}

        for competitor in competitors:
            # Get player name
            if 'athlete' not in competitor:
                continue

            player_name = competitor['athlete'].get('displayName')

            if not player_name:
                continue

            # Get earnings
            earnings = competitor.get('earnings', 0)

            # Only include players with positive earnings
            if earnings and earnings > 0:
                earnings_data[player_name] = int(earnings)

        return earnings_data

    except Exception as e:
        return {}


if __name__ == "__main__":
    # Test with The Sentry 2024
    print("=" * 80)
    print("TESTING EARNINGS SCRAPER")
    print("=" * 80)

    test_tournaments = [
        ('401580329', 'The Sentry 2024'),
        ('401580330', 'Sony Open 2024'),
    ]

    for tournament_id, name in test_tournaments:
        print(f"\n{name} ({tournament_id}):")
        print("-" * 80)

        earnings = scrape_tournament_earnings(tournament_id)

        if earnings:
            print(f"Found earnings for {len(earnings)} players")
            # Show top 5
            sorted_earnings = sorted(earnings.items(), key=lambda x: x[1], reverse=True)[:5]
            for player, amount in sorted_earnings:
                print(f"  {player}: ${amount:,}")
        else:
            print("No earnings data found")

        time.sleep(2)  # Be nice to ESPN

    print("\n" + "=" * 80)
