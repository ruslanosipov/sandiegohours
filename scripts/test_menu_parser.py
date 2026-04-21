#!/usr/bin/env python3
"""
Test menu parser with The Hangout's happy hour menu.
"""

import requests
import json
import re

# OpenRouter API key (same as scrape_websites_ai.py)
API_KEY = "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"

# The Hangout happy hour page
MENU_URL = 'http://www.thehangoutrestaurantandbar.com/happy-hour-menu'

def fetch_menu():
    """Fetch menu HTML."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(MENU_URL, headers=headers, timeout=30)
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

def parse_with_ai(text_content):
    """Send to OpenRouter AI."""
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
  "food": {{"name": "item name with price", "price": 6.00}}
}}

Examples:
{{"drink": {{"name": "$5 bottled beer", "price": 5}}, "food": {{"name": "$1 wings", "price": 1}}}}
{{"drink": {{"name": "$7 draft pours", "price": 7}}, "food": {{"name": "$3 chicken sliders", "price": 3}}}}

Find the CHEAPEST drink and CHEAPEST food item. Return the concise format shown in examples. If no prices, use null."""

    response = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers=headers,
        json={
            'model': 'google/gemma-3-4b-it:free',
            'messages': [
                {'role': 'system', 'content': 'You are a menu parser. Extract happy hour items with prices. Return JSON only.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.1,
        },
        timeout=60
    )
    
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
    
    return result

if __name__ == '__main__':
    main()
