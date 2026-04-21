#!/usr/bin/env python3
"""
Test menu parser with The Hangout's happy hour menu.
"""

import requests
import json
import re
import time

# OpenRouter API key (same as scrape_websites_ai.py)
API_KEY = "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"

BASE_URL = 'http://www.thehangoutrestaurantandbar.com'

# Priority order: happy hour first, then menu pages
PRIORITY_PATHS = [
    '/happy-hour',
    '/happyhour', 
    '/hh',
    '/specials',
    '/menu',
    '/drinks',
    '/bar',
]

def find_menu_page(base_url):
    """Find happy hour or menu page by checking priority paths and links."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # First, try priority paths directly
    print("Checking priority paths...")
    for path in PRIORITY_PATHS:
        url = f"{base_url}{path}"
        try:
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                print(f"Found: {url}")
                return url
        except:
            pass
    
    # If no direct hits, scrape the homepage for links
    print("Searching homepage for menu links...")
    try:
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text.lower()
        
        # Look for happy hour links
        hh_patterns = [
            r'href="([^"]*happy[-_]?hour[^"]*)"',
            r'href="([^"]*hh[^"]*)"',
            r'href="([^"]*specials[^"]*)"',
            r'href="([^"]*menu[^"]*)"',
            r'href="([^"]*drinks[^"]*)"',
        ]
        
        for pattern in hh_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                # Handle relative and absolute URLs
                if match.startswith('http'):
                    return match
                elif match.startswith('/'):
                    return f"{base_url}{match}"
                else:
                    return f"{base_url}/{match}"
    except Exception as e:
        print(f"Error searching homepage: {e}")
    
    # Fallback: return base URL and let AI parse the homepage
    print("No menu page found, using homepage")
    return base_url

def fetch_menu():
    """Fetch menu HTML from discovered page."""
    menu_url = find_menu_page(BASE_URL)
    print(f"Fetching: {menu_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(menu_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def clean_html(html):
    """Clean HTML to text."""
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    # Remove tags
    html = re.sub(r'<[^>]+>', ' ', html)
    # Normalize whitespace
    html = re.sub(r'\s+', ' ', html)
    return html[:8000]  # Limit length

def parse_with_ai(text_content, max_retries=3):
    """Send to OpenRouter AI with retry logic."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://happy-hour-finder.local",
        "X-Title": "Happy Hour Finder",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Parse this happy hour menu from The Hangout Restaurant and Bar.

Menu content:
{text_content}

Extract drink and food items with prices. Look for patterns like:
- $5 bottled beer, $7 draft, $8 cocktails
- $1 wings, $3 sliders, $8 nachos

Return JSON in this exact format:
{{
  "drink": {{"name": "item name with price", "price": 5.00}},
  "food": {{"name": "item name with price", "price": 6.00}},
  "short_summary": "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"
}}

Examples:
{{"drink": {{"name": "$5 bottled beer", "price": 5}}, "food": {{"name": "$1 wings", "price": 1}}, "short_summary": "$1 wings, $3 sliders, $5 bottled and $7 cocktails"}}
{{"drink": {{"name": "$7 draft pours", "price": 7}}, "food": {{"name": "$3 chicken sliders", "price": 3}}, "short_summary": "$3 sliders, $6 nachos, $7 draft and $9 cocktails"}}

Rules:
- Find the CHEAPEST drink and CHEAPEST food item
- short_summary must be UNDER 20 words
- Order by price: drinks and foods mixed, cheapest first
- Example: "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"

If no prices, use null."""

    for attempt in range(max_retries):
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={
                    'model': 'openrouter/free',
                    'messages': [
                        {'role': 'system', 'content': 'You are a menu parser. Extract happy hour items with prices. Return JSON only.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.1,
                },
                timeout=60
            )
            
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)  # Exponential backoff
                    continue
                else:
                    raise Exception("Rate limited after max retries")
                
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Request failed: {e}, retrying...")
            time.sleep(2 ** (attempt + 1))
    
    content = data['choices'][0]['message']['content']
    
    # Extract JSON
    json_match = re.search(r'```json\n?(.*?)\n?```', content, re.DOTALL) or \
                 re.search(r'```\n?(.*?)\n?```', content, re.DOTALL) or \
                 re.search(r'(\{[\s\S]*\})', content)
    
    if json_match:
        return json.loads(json_match.group(1).strip())
    return json.loads(content.strip())

def main():
    print("Fetching The Hangout happy hour menu...")
    html = fetch_menu()
    print(f"Fetched {len(html)} bytes")
    
    print("\nCleaning HTML...")
    text = clean_html(html)
    print(f"Cleaned text: {len(text)} chars")
    
    print("\nParsing with AI...")
    result = parse_with_ai(text)
    
    print("\n=== CHEAPEST ITEMS ===")
    print(f"Drink: {result.get('drink', 'Not found')}")
    print(f"Food: {result.get('food', 'Not found')}")
    print(f"\nSummary: {result.get('short_summary', 'N/A')}")
    print(f"Summary word count: {len(result.get('short_summary', '').split())}")
    
    return result

if __name__ == '__main__':
    main()
