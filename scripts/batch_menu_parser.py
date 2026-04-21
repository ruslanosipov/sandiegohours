#!/usr/bin/env python3
# -*- coding: utf-8 -*
"""
Batch process restaurants to find cheapest happy hour items.
Process 10 restaurants from the happy_hours.csv
"""

import csv
import json
import re
import time
import requests
from pathlib import Path

API_KEY = "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"

PRIORITY_PATHS = [
    '/happy-hour',
    '/happyhour',
    '/hh',
    '/specials',
    '/menu',
    '/drinks',
    '/bar',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def find_menu_page(base_url):
    """Find happy hour or menu page."""
    if not base_url:
        return None
        
    for path in PRIORITY_PATHS:
        url = f"{base_url.rstrip('/')}{path}"
        try:
            response = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return url
        except:
            pass
    return base_url

def clean_html(html):
    """Clean HTML to text."""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html[:8000]

def parse_with_ai(restaurant_name, text_content, max_retries=3):
    """Send to OpenRouter AI with retry logic."""
    prompt = f"""Parse this happy hour menu from {restaurant_name}.

Menu content:
{text_content}

Extract ALL drink and food items with prices you can find. Look for patterns like:
- $5 bottled beer, $7 draft, $8 cocktails
- $1 wings, $3 sliders, $8 nachos

Return JSON in this exact format:
{{
  "drink": {{"name": "cheapest drink with price", "price": 5.00}},
  "food": {{"name": "cheapest food with price", "price": 6.00}},
  "short_summary": "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"
}}

Examples:
{{"drink": {{"name": "$5 bottled beer", "price": 5}}, "food": {{"name": "$1 wings", "price": 1}}, "short_summary": "$1 wings, $5 bottled and $7 cocktails"}}
{{"drink": {{"name": "$7 draft pours", "price": 7}}, "food": {{"name": "$3 chicken sliders", "price": 3}}, "short_summary": "$3 sliders, $7 draft and $9 cocktails"}}

Rules:
- Find the CHEAPEST drink and CHEAPEST food item
- Include 3-5 popular items in short_summary
- short_summary must be UNDER 15 words
- Order by price: cheapest first
- Use "and" before last item

If no happy hour prices found, return null for drink and food, and empty string for short_summary."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://happy-hour-finder.local",
        "X-Title": "Happy Hour Finder",
        "Content-Type": "application/json"
    }
    
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
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    print("  Rate limited after max retries")
                    return None
                
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            
            # Extract JSON
            json_match = re.search(r'```json\n?(.*?)\n?```', content, re.DOTALL) or \
                         re.search(r'```\n?(.*?)\n?```', content, re.DOTALL) or \
                         re.search(r'(\{[\s\S]*\})', content)
            
            if json_match:
                return json.loads(json_match.group(1).strip())
            return json.loads(content.strip())
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  Error after retries: {e}")
                return None
            time.sleep(2 ** (attempt + 1))
    
    return None

def process_restaurant(name, website_url):
    """Process a single restaurant."""
    print(f"\n{'='*60}")
    print(f"Processing: {name}")
    print(f"Website: {website_url}")
    
    if not website_url:
        print("  SKIP: No website")
        return None
    
    menu_url = find_menu_page(website_url)
    if not menu_url:
        print("  SKIP: No menu page found")
        return None
    
    print(f"  Menu URL: {menu_url}")
    
    try:
        response = requests.get(menu_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        text = clean_html(html)
        print(f"  Fetched {len(html)} bytes, cleaned to {len(text)} chars")
        
        result = parse_with_ai(name, text)
        if result:
            print(f"  [OK] Drink: {result.get('drink', 'N/A')}")
            print(f"  [OK] Food: {result.get('food', 'N/A')}")
            print(f"  [OK] Summary: {result.get('short_summary', 'N/A')}")
        else:
            print("  [FAIL] No results from AI")
        
        return result
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def main():
    # Load first 10 restaurants
    csv_path = Path(__file__).parent.parent / 'public' / 'happy_hours.csv'
    restaurants = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 10:
                break
            restaurants.append({
                'name': row['restaurant_name'],
                'website': row.get('website_url', '')
            })
    
    print(f"Processing {len(restaurants)} restaurants...")
    
    results = []
    for r in restaurants:
        result = process_restaurant(r['name'], r['website'])
        results.append({
            'restaurant_name': r['name'],
            'website': r['website'],
            'data': result
        })
        
        # Delay between requests to be nice to APIs
        time.sleep(2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    for r in results:
        data = r['data']
        if data and (data.get('drink') or data.get('food')):
            drink = data.get('drink', {})
            food = data.get('food', {})
            summary = data.get('short_summary', '')
            print(f"\n{r['restaurant_name']}:")
            print(f"  Drink: {drink.get('name', 'N/A')} (${drink.get('price')})")
            print(f"  Food: {food.get('name', 'N/A')} (${food.get('price')})")
            print(f"  Summary: {summary}")
        else:
            print(f"\n{r['restaurant_name']}: No data")

if __name__ == '__main__':
    main()
