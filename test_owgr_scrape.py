"""
Test scraping OWGR data - check for API endpoints or downloadable files
"""

import requests
from bs4 import BeautifulSoup
import json

# Try the main page
url = "https://www.owgr.com/current-world-ranking"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("=" * 80)
print("CHECKING OWGR WEBSITE FOR DATA ACCESS")
print("=" * 80)

response = requests.get(url, headers=headers)
print(f"\nStatus Code: {response.status_code}")

soup = BeautifulSoup(response.content, 'html.parser')

# Look for API endpoints in script tags
print("\n" + "=" * 80)
print("SEARCHING FOR API ENDPOINTS IN SCRIPTS")
print("=" * 80)

scripts = soup.find_all('script')
api_urls = []

for script in scripts:
    if script.string:
        # Look for API URLs
        if 'api' in script.string.lower() or 'endpoint' in script.string.lower():
            lines = script.string.split('\n')
            for line in lines[:5]:  # First 5 lines
                if 'http' in line or 'api' in line.lower():
                    print(line.strip()[:100])

# Check for download links
print("\n" + "=" * 80)
print("SEARCHING FOR DOWNLOAD LINKS")
print("=" * 80)

links = soup.find_all('a', href=True)
download_links = []

for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)

    if any(ext in href.lower() for ext in ['.csv', '.xlsx', '.xls', '.json', 'download', 'export']):
        print(f"Found: {text} -> {href}")
        download_links.append(href)

# Try common API patterns
print("\n" + "=" * 80)
print("TRYING COMMON API PATTERNS")
print("=" * 80)

api_patterns = [
    "https://www.owgr.com/api/ranking",
    "https://api.owgr.com/ranking",
    "https://www.owgr.com/api/current-ranking",
    "https://www.owgr.com/api/players",
]

for api_url in api_patterns:
    try:
        resp = requests.get(api_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            print(f"\nFOUND working endpoint: {api_url}")
            print(f"  Response length: {len(resp.content)} bytes")
            print(f"  Content type: {resp.headers.get('content-type')}")

            # Try to parse as JSON
            try:
                data = resp.json()
                print(f"  JSON keys: {list(data.keys())[:5]}")
            except:
                print(f"  First 200 chars: {resp.text[:200]}")
        else:
            print(f"FAILED {api_url} - Status {resp.status_code}")
    except Exception as e:
        print(f"FAILED {api_url} - Error: {str(e)[:50]}")

print("\n" + "=" * 80)
