"""
Google Places API (New) v1 fetcher for restaurant data with happy hour support.
Uses Places API v1 with field masks to get secondaryOpeningHours (happy hours).
"""
import requests
from typing import List, Optional, Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage import Restaurant

GOOGLE_PLACES_API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"
PLACES_API_BASE = "https://places.googleapis.com/v1"


def get_place_details_new(place_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Get place details using Places API (New) v1.
    
    Args:
        place_id: Google place ID
        api_key: API key
        
    Returns:
        Place details including secondaryOpeningHours
    """
    # Place ID might need to be URL-encoded or have specific format
    # Try with just the ID first
    url = f"{PLACES_API_BASE}/places/{place_id}"
    print(f"    URL: {url[:80]}...")
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        # Request specific fields - use camelCase for v1 API
        # Try currentSecondaryOpeningHours for happy hours
        "X-Goog-FieldMask": "id,displayName,formattedAddress,types,nationalPhoneNumber,websiteUri,regularOpeningHours,currentSecondaryOpeningHours"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"    API Error: {response.status_code}")
        print(f"    Response: {response.text[:500]}")
        return None
    
    return response.json()


def parse_secondary_opening_hours(secondary_hours: List[Dict]) -> Optional[str]:
    """
    Parse secondary opening hours to find happy hours.
    
    The API returns currentSecondaryOpeningHours as a list where each entry has:
    - openNow: boolean
    - periods: list of periods with open/close times
    - weekdayDescriptions: list of strings like "Monday: 3:00 PM – 6:00 PM"
    - secondaryHoursType: str (e.g., "HAPPY_HOUR", "KITCHEN", "DELIVERY")
    
    Args:
        secondary_hours: List of SecondaryOpeningHour from API
        
    Returns:
        Formatted happy hour string or None
    """
    if not secondary_hours or not isinstance(secondary_hours, list):
        return None
    
    for entry in secondary_hours:
        # Check if this entry is for happy hour
        hours_type = entry.get('secondaryHoursType', '').upper()
        if hours_type == 'HAPPY_HOUR':
            # Get weekday descriptions
            descriptions = entry.get('weekdayDescriptions', [])
            if descriptions:
                return ' | '.join(descriptions)
            
            # Fallback: build from periods
            periods = entry.get('periods', [])
            if periods:
                parts = []
                for period in periods:
                    open_info = period.get('open', {})
                    close_info = period.get('close', {})
                    
                    day = open_info.get('day', '')
                    open_time = f"{open_info.get('hour', 0):02d}:{open_info.get('minute', 0):02d}"
                    close_time = f"{close_info.get('hour', 0):02d}:{close_info.get('minute', 0):02d}"
                    
                    if day is not None:
                        parts.append(f"Day {day}: {open_time} - {close_time}")
                
                if parts:
                    return ' | '.join(parts)
    
    return None


def search_places_new(location: str, radius: int = 2400, api_key: str = None, page_token: str = None) -> List[Dict]:
    """
    Search for places using Places API (New) v1 nearby search.
    
    Args:
        location: "lat,lng" string
        radius: Search radius in meters
        api_key: API key
        
    Returns:
        List of place results
    """
    url = f"{PLACES_API_BASE}/places:searchNearby"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key or GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.types,places.primaryType"
    }
    
    body = {
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(location.split(',')[0]),
                    "longitude": float(location.split(',')[1])
                },
                "radius": radius
            }
        },
        "includedTypes": ["restaurant", "bar"],
        "maxResultCount": 20  # Google limit per page
    }
    
    response = requests.post(url, headers=headers, json=body, timeout=30)
    
    if response.status_code != 200:
        print(f"Search API Error: {response.status_code} - {response.text[:200]}")
        return []
    
    data = response.json()
    return data.get('places', [])


def convert_to_restaurant(place_data: Dict[str, Any]) -> Restaurant:
    """
    Convert Places API v1 response to Restaurant model.
    
    Args:
        place_data: API response for a single place
        
    Returns:
        Restaurant instance
    """
    # Extract display name
    name = place_data.get('displayName', {}).get('text', '')
    
    # Get address
    address = place_data.get('formattedAddress', '')
    
    # Get phone and website
    phone = place_data.get('nationalPhoneNumber', '')
    website = place_data.get('websiteUri', '')
    
    # Parse regular opening hours
    regular_hours = ""
    reg_hours = place_data.get('regularOpeningHours', {})
    if reg_hours:
        descriptions = reg_hours.get('weekdayDescriptions', [])
        if descriptions:
            regular_hours = ' | '.join(descriptions)
    
    # Parse happy hours from current secondary opening hours
    happy_hour_times = ""
    sec_hours = place_data.get('currentSecondaryOpeningHours', [])
    hh_result = parse_secondary_opening_hours(sec_hours)
    if hh_result:
        happy_hour_times = hh_result
        try:
            print(f"    [OK] Found happy hours: {hh_result[:60]}...")
        except UnicodeEncodeError:
            print(f"    [OK] Found happy hours: (unicode characters)")
    
    # Determine source
    source = 'Google Places API'
    if happy_hour_times:
        source = 'Google Places API (Happy Hours)'
    
    # Get location if available
    location = place_data.get('location', {})
    
    return Restaurant(
        restaurant_name=name,
        address=address,
        phone_number=phone,
        website_url=website,
        happy_hour_times=happy_hour_times,
        regular_hours=regular_hours,
        rating=str(place_data.get('rating', '')),
        review_count=str(place_data.get('userRatingCount', '')),
        price_level=str(place_data.get('priceLevel', '')),
        source=source,
        freshness_date='',  # Will be set by caller
        latitude=str(location.get('latitude', '')) if location else '',
        longitude=str(location.get('longitude', '')) if location else ''
    )


def fetch_92116_restaurants(api_key: str = None, max_results: int = 60) -> List[Restaurant]:
    """
    Fetch restaurants in 92116 area with happy hour data from Google Places API (New).
    
    Args:
        api_key: Optional API key (uses default if not provided)
        max_results: Maximum results to fetch (Google limit is 60)
        
    Returns:
        List of Restaurant instances with happy hour data where available
    """
    api_key = api_key or GOOGLE_PLACES_API_KEY
    location = "32.762889,-117.119922"  # 2861 Copley Ave
    
    print(f"Fetching restaurants near {location} using Places API v1...")
    print(f"Radius: 2400m (30-min walk), Max results: {max_results}")
    
    # Search for places - may need multiple pages
    all_places = []
    page_token = None
    
    while len(all_places) < max_results:
        places = search_places_new(location, radius=2400, api_key=api_key, page_token=page_token)
        if not places:
            break
        all_places.extend(places)
        print(f"  Found {len(places)} places (total: {len(all_places)})")
        if len(all_places) >= max_results:
            break
        # Check for next page token (would need to implement pagination in search_places_new)
        break  # For now, just use first page
    
    print(f"Processing {len(all_places)} places...")
    
    restaurants = []
    hh_count = 0
    
    for i, place_summary in enumerate(all_places, 1):
        place_id = place_summary.get('id')
        name = place_summary.get('displayName', {}).get('text', 'Unknown')
        
        print(f"[{i}/{len(all_places)}] Processing {name}...")
        
        # Get full details
        details = get_place_details_new(place_id, api_key)
        if not details:
            continue
        
        try:
            restaurant = convert_to_restaurant(details)
            restaurants.append(restaurant)
            if restaurant.happy_hour_times:
                hh_count += 1
        except Exception as e:
            print(f"    Error converting: {e}")
            continue
    
    print(f"\nTotal: {len(restaurants)} restaurants")
    print(f"With happy hours: {hh_count}")
    
    return restaurants


if __name__ == '__main__':
    # Test
    results = fetch_92116_restaurants()
    for r in results[:3]:
        try:
            print(f"\n{r.restaurant_name}:")
            print(f"  HH: {r.happy_hour_times or 'None'}")
        except UnicodeEncodeError:
            print(f"\n{r.restaurant_name}:")
            print(f"  HH: (unicode)")
