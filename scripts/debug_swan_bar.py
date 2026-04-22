#!/usr/bin/env python3
"""Debug script to check Swan Bar's API response."""
import requests
import json

API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"
PLACES_API_BASE = "https://places.googleapis.com/v1"

# Search for Swan Bar
search_url = f"{PLACES_API_BASE}/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "places.id,places.displayName"
}

body = {
    "textQuery": "Swan Bar San Diego Normal Heights",
    "locationBias": {
        "circle": {
            "center": {"latitude": 32.762889, "longitude": -117.119922},
            "radius": 500.0
        }
    }
}

response = requests.post(search_url, headers=headers, json=body)
data = response.json()

print("Search results:")
print(json.dumps(data, indent=2)[:1000])

if data.get('places'):
    place = data['places'][0]
    place_id = place['id']
    print(f"\n\nFound place: {place['displayName']['text']}")
    print(f"Place ID: {place_id}")
    
    # Get full details with ALL possible hour fields
    details_url = f"{PLACES_API_BASE}/places/{place_id}"
    details_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        # Request ALL hour-related fields
        "X-Goog-FieldMask": "id,displayName,formattedAddress,regularOpeningHours,currentSecondaryOpeningHours"
    }
    
    details_resp = requests.get(details_url, headers=details_headers)
    details = details_resp.json()
    
    print("\n\nFull details:")
    print(json.dumps(details, indent=2))
