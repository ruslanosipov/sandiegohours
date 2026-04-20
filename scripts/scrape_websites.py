#!/usr/bin/env python3
"""
Scrape websites for happy hour data
Use website as source of truth when found
"""
import re
import csv
import time
import random
from datetime import datetime
import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

def scrape_website(url, name):
    """Scrape website for happy hour info"""
    if not url:
        return None
    
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        text = resp.text.lower()
        
        # Look for happy hour mentions with time patterns
        matches = re.findall(r'[^.\n]*happy\s*hour[^.\n]{0,120}', text)
        
        if matches:
            for match in matches:
                # Check if it has time info
                if re.search(r'\d{1,2}[\s:]?(?::\d{2})?\s*(?:am|pm)', match, re.IGNORECASE):
                    clean = re.sub(r'\s+', ' ', match).strip()
                    return clean[:200]
        
        return None
        
    except Exception as e:
        return None

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
    
    print(f"Places to scrape: {len(to_scrape)}")
    updated = []
    
    for i, place in enumerate(to_scrape, 1):
        name = place.get('restaurant_name', '')
        website = place.get('website_url', '')
        
        print(f"[{i}/{len(to_scrape)}] {name}")
        
        hh_text = scrape_website(website, name)
        
        if hh_text:
            place['happy_hour_times'] = hh_text
            place['source'] = 'google_maps_api+website_scraped'
            place['freshness_date'] = datetime.now().strftime('%Y-%m-%d')
            updated.append(name)
            print(f"  [FOUND] {hh_text[:60]}...")
        
        time.sleep(0.5)
    
    # Write back
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=places[0].keys())
        writer.writeheader()
        writer.writerows(places)
    
    print(f"\nUpdated {len(updated)} places from websites")
    return updated

if __name__ == "__main__":
    scrape_all()
