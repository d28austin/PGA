"""
Test the updated earnings scraper
"""

from scrape_espn_earnings import scrape_tournament_earnings

print('=' * 80)
print('TESTING UPDATED SCRAPER')
print('=' * 80)
print()

# Test 2022 Farmers Insurance Open
print('2022 Farmers Insurance Open (401353234):')
print('-' * 80)

earnings = scrape_tournament_earnings('401353234')

if earnings:
    print(f'Found {len(earnings)} players with earnings')
    print()

    print('Top 10:')
    for i, (name, amount) in enumerate(sorted(earnings.items(), key=lambda x: x[1], reverse=True)[:10], 1):
        print(f'{i:2}. {name:25} ${amount:,}')

    # Check for Jon Rahm specifically
    print()
    if 'Jon Rahm' in earnings:
        print(f"Jon Rahm's earnings: ${earnings['Jon Rahm']:,}")
    else:
        print("Jon Rahm not found in earnings data")
else:
    print('No earnings data found')
