"""
Check if API response has earnings data
"""

import json

with open('api_response_2.json', 'r') as f:
    data = json.load(f)

event = data['events'][0]
comp = event['competitions'][0]
competitors = comp['competitors']

print(f'Total competitors: {len(competitors)}')
print()

# Check how many have earnings
with_earnings = [c for c in competitors if c.get('earnings', 0) > 0]
print(f'Players with earnings > 0: {len(with_earnings)}')
print()

if len(with_earnings) > 0:
    print('=' * 80)
    print('TOP 10 EARNERS')
    print('=' * 80)

    sorted_by_earnings = sorted(with_earnings, key=lambda x: x.get('earnings', 0), reverse=True)

    for i, c in enumerate(sorted_by_earnings[:10], 1):
        name = c['athlete']['displayName']
        position = c['status']['position']['displayName']
        earnings = c.get('earnings', 0)

        print(f'{i:2}. {name:25} Pos: {position:3} | ${earnings:,.0f}')
else:
    print('No players with earnings found')
