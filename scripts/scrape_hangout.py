#!/usr/bin/env python3
"""
Reset The Hangout's happy hour data and scrape it fresh with AI
"""
import csv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_websites_ai import scrape_restaurant

# Reset The Hangout's data
csv_path = "public/happy_hours.csv"
places = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        places.append(row)

# Find and reset The Hangout
for place in places:
    if "hangout" in place.get('restaurant_name', '').lower():
        print(f"Resetting: {place['restaurant_name']}")
        place['happy_hour_times'] = ''
        place['source'] = ''
        
        # Now scrape it
        print("Scraping website with AI...")
        hh_text, status = scrape_restaurant(place['restaurant_name'], place['website_url'])
        
        if hh_text:
            place['happy_hour_times'] = hh_text
            place['source'] = 'Website'
            place['freshness_date'] = '2026-04-19'
            print(f"[FOUND] {hh_text}")
        else:
            print(f"[NOT FOUND - {status}]")
        
        break

# Write back
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=places[0].keys())
    writer.writeheader()
    writer.writerows(places)

print("Done!")
