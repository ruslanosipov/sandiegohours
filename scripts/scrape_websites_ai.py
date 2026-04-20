#!/usr/bin/env python3
"""
Scrape websites for happy hour data using AI to parse HTML
Uses OpenRouter API to extract structured happy hour info from messy website text
"""
import re
import csv
import time
import random
import json
from datetime import datetime
import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# OpenRouter API for free AI models
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "Authorization": "Bearer sk-or-v1-demo",  # Replace with actual key
    "HTTP-Referer": "https://happy-hour-finder.local",
    "X-Title": "Happy Hour Finder",
    "Content-Type": "application/json"
}

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

def fetch_website_text(url: str) -> str:
    """Fetch and extract text from website"""
    if not url:
        return ""
    
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        resp.raise_for_status()
        # Simple text extraction - remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:4000]  # Limit for API
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return ""

def parse_with_ai(text: str, restaurant_name: str) -> dict:
    """Use AI to parse happy hour info from website text"""
    
    prompt = f"""Extract happy hour information for {restaurant_name} from this website text.

Text snippet:
{text}

Extract and return ONLY a JSON object with this exact format:
{{
  "has_happy_hour": true/false,
  "schedule": {{
    "Monday": "time range or 'Closed'",
    "Tuesday": "time range or 'Closed'",
    "Wednesday": "time range or 'Closed'",
    "Thursday": "time range or 'Closed'", 
    "Friday": "time range or 'Closed'",
    "Saturday": "time range or 'Closed'",
    "Sunday": "time range or 'Closed'"
  }},
  "notes": "any special notes about drinks/food deals"
}}

Use "Closed" for days with no happy hour. Time format should be like "3:00 PM - 6:00 PM". If unsure, use empty string "".
Return ONLY the JSON, no other text."""

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=OPENROUTER_HEADERS,
            json={
                "model": "google/gemma-3-4b-it:free",  # Free model
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return {"has_happy_hour": False, "schedule": {}, "notes": ""}
        
    except Exception as e:
        print(f"    AI parsing error: {e}")
        return {"has_happy_hour": False, "schedule": {}, "notes": ""}

def format_schedule(schedule: dict) -> str:
    """Convert AI schedule to pipe-separated format"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    parts = []
    for day in days:
        time_range = schedule.get(day, "")
        if time_range:
            parts.append(f"{day}: {time_range}")
        else:
            parts.append(f"{day}: Closed")
    return " | ".join(parts)

def scrape_restaurant(name: str, url: str) -> tuple:
    """Scrape a single restaurant's website for happy hour info"""
    print(f"  Fetching website...")
    text = fetch_website_text(url)
    
    if not text:
        return None, "no_website"
    
    if "happy hour" not in text.lower():
        return None, "no_mention"
    
    print(f"  Parsing with AI...")
    result = parse_with_ai(text, name)
    
    if not result.get("has_happy_hour"):
        return None, "ai_no_data"
    
    schedule = result.get("schedule", {})
    if not schedule:
        return None, "no_schedule"
    
    formatted = format_schedule(schedule)
    return formatted, "ai_parsed"

def scrape_all():
    """Scrape all places with websites that don't have happy hour data"""
    csv_path = "public/happy_hours.csv"
    
    places = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            places.append(row)
    
    # Find places without happy hour data but with websites
    to_scrape = [p for p in places if not p.get('happy_hour_times', '').strip() and p.get('website_url')]
    
    print(f"Places to scrape: {len(to_scrape)}\n")
    
    updated = []
    stats = {"no_website": 0, "no_mention": 0, "ai_no_data": 0, "no_schedule": 0, "success": 0}
    
    for i, place in enumerate(to_scrape, 1):
        name = place.get('restaurant_name', '')
        website = place.get('website_url', '')
        
        print(f"[{i}/{len(to_scrape)}] {name}")
        
        hh_text, status = scrape_restaurant(name, website)
        stats[status] = stats.get(status, 0) + 1
        
        if hh_text:
            place['happy_hour_times'] = hh_text
            place['source'] = 'google_maps_api+website_ai'
            place['freshness_date'] = datetime.now().strftime('%Y-%m-%d')
            updated.append(name)
            print(f"  [FOUND] {hh_text[:80]}...")
        else:
            print(f"  [{status.upper().replace('_', ' ')}]")
        
        time.sleep(1)  # Be nice to APIs
    
    # Write back
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=places[0].keys())
        writer.writeheader()
        writer.writerows(places)
    
    print(f"\n{'='*60}")
    print(f"Updated {len(updated)} places from websites using AI")
    print(f"Stats: {stats}")
    if updated:
        print(f"\nUpdated places:")
        for name in updated:
            print(f"  - {name}")
    
    return updated

if __name__ == "__main__":
    scrape_all()
