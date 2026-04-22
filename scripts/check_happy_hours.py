#!/usr/bin/env python3
"""Check multiple places for secondary_opening_hours."""
import requests
import json
import time

API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"

# Search for places
url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
params = {
    'location': '32.762889,-117.119922',
    'radius': 1500,
    'type': 'restaurant|bar',
    'key': API_KEY
}

response = requests.get(url, params=params)
data = response.json()

places = data.get('results', [])
print(f"Checking {len(places)} places for happy hours...\n")

hh_count = 0
for place in places[:15]:  # Check first 15
    name = place['name']
    place_id = place['place_id']
    
    # Get details
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place_id,
        'fields': 'name,secondary_opening_hours',
        'key': API_KEY
    }
    
    details_resp = requests.get(details_url, params=details_params)
    details = details_resp.json()
    time.sleep(0.2)  # Rate limit
    
    if details.get('status') == 'OK':
        soh = details['result'].get('secondary_opening_hours')
        if soh:
            print(f"[OK] {name}: HAS secondary_opening_hours")
            print(f"     Type: {type(soh)}")
            print(f"     Data: {json.dumps(soh)[:200]}...")
            print()
            hh_count += 1
        else:
            print(f"[--] {name}: No secondary_opening_hours")
    else:
        print(f"[ERR] {name}: {details.get('status')}")

print(f"\n\nTotal with happy hours: {hh_count}/{len(places[:15])}")
