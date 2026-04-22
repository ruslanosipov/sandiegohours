#!/usr/bin/env python3
"""Find a place with happy hours and check API response."""
import requests
import json

API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"

# Search for bars in Normal Heights
url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
params = {
    'location': '32.762889,-117.119922',
    'radius': 1500,
    'type': 'bar',
    'keyword': 'happy hour',
    'key': API_KEY
}

response = requests.get(url, params=params)
data = response.json()

print(f"Found {len(data.get('results', []))} places")

if data.get('results'):
    place = data['results'][0]
    print(f"\nFirst place: {place['name']}")
    print(f"Place ID: {place['place_id']}")
    
    # Get details
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place['place_id'],
        'fields': 'name,opening_hours,secondary_opening_hours',
        'key': API_KEY
    }
    
    details_resp = requests.get(details_url, params=details_params)
    details = details_resp.json()
    
    if details.get('status') == 'OK':
        result = details['result']
        print("\n\nOpening hours:")
        print(json.dumps(result.get('opening_hours'), indent=2)[:500])
        print("\n\nSecondary opening hours:")
        soh = result.get('secondary_opening_hours')
        print(json.dumps(soh, indent=2) if soh else "None")
        print(f"\nType: {type(soh)}")
