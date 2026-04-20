#!/usr/bin/env python3
"""
Add latitude and longitude to happy_hours.csv using Google Maps API.

This script reads the existing CSV, fetches coordinates for each place
from the Places API, and writes an updated CSV with lat/lng columns.
"""

import os
import csv
import time
from datetime import datetime
from typing import Optional
import requests

API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"

PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_FIND_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

INPUT_FILE = "public/happy_hours.csv"
OUTPUT_FILE = "public/happy_hours_with_coords.csv"


def get_place_details(name: str, address: str) -> Optional[dict]:
    """Get place details including coordinates from Places API."""
    search_text = f"{name} {address}"
    
    # First, search for the place
    find_params = {
        'input': search_text,
        'inputtype': 'textquery',
        'fields': 'place_id',
        'key': API_KEY,
    }
    
    try:
        find_resp = requests.get(PLACES_FIND_URL, params=find_params, timeout=30)
        find_data = find_resp.json()
        
        if find_data.get('status') != 'OK' or not find_data.get('candidates'):
            return None
        
        place_id = find_data['candidates'][0]['place_id']
        
        # Get details including geometry
        details_params = {
            'place_id': place_id,
            'fields': 'geometry,place_id',
            'key': API_KEY,
        }
        
        details_resp = requests.get(PLACES_DETAILS_URL, params=details_params, timeout=30)
        details_data = details_resp.json()
        
        if details_data.get('status') == 'OK' and 'result' in details_data:
            geometry = details_data['result'].get('geometry', {})
            location = geometry.get('location', {})
            return {
                'lat': location.get('lat'),
                'lng': location.get('lng'),
            }
        
        return None
    
    except Exception as e:
        print(f"  Error fetching details: {e}")
        return None


def add_coordinates():
    """Main function to add coordinates to CSV."""
    # Read existing CSV
    places = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            places.append(row)
    
    # Add new columns if they don't exist
    if 'latitude' not in fieldnames:
        fieldnames.extend(['latitude', 'longitude'])
    
    print(f"Processing {len(places)} places...")
    
    # Fetch coordinates for each place
    updated_count = 0
    for i, place in enumerate(places, 1):
        name = place.get('restaurant_name', '')
        address = place.get('address', '')
        
        print(f"[{i}/{len(places)}] {name[:50]}")
        
        # Skip if already has coordinates
        if place.get('latitude') and place.get('longitude'):
            print(f"  Already has coordinates, skipping")
            continue
        
        coords = get_place_details(name, address)
        
        if coords:
            place['latitude'] = coords['lat']
            place['longitude'] = coords['lng']
            updated_count += 1
            print(f"  Coordinates: {coords['lat']:.6f}, {coords['lng']:.6f}")
        else:
            place['latitude'] = ''
            place['longitude'] = ''
            print(f"  No coordinates found")
        
        time.sleep(0.1)  # Rate limiting
    
    # Write updated CSV
    print(f"\nWriting {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(places)
    
    print(f"\nSummary:")
    print(f"  Total places: {len(places)}")
    print(f"  Updated with coordinates: {updated_count}")


if __name__ == '__main__':
    add_coordinates()
