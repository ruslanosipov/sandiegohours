"""
Google Places API (New) v1 fetcher for restaurant data with happy hour support.
Uses Places API v1 text search with pagination to get more than 20 results.
"""
import math
import requests
import time
from typing import List, Optional, Dict, Any

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage import Restaurant

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

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
    url = f"{PLACES_API_BASE}/places/{place_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "id,displayName,formattedAddress,types,nationalPhoneNumber,websiteUri,regularOpeningHours,currentSecondaryOpeningHours,rating,userRatingCount,priceLevel,location,googleMapsUri,editorialSummary"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"    API Error: {response.status_code}")
        return None
    
    return response.json()


def parse_secondary_opening_hours(secondary_hours: List[Dict]) -> Optional[str]:
    """
    Parse secondary opening hours to find happy hours.
    
    Args:
        secondary_hours: List of SecondaryOpeningHour from API
        
    Returns:
        Formatted happy hour string or None
    """
    if not secondary_hours or not isinstance(secondary_hours, list):
        return None
    
    for entry in secondary_hours:
        hours_type = entry.get('secondaryHoursType', '').upper()
        if hours_type == 'HAPPY_HOUR':
            descriptions = entry.get('weekdayDescriptions', [])
            if descriptions:
                return ' | '.join(descriptions)
    
    return None


def search_places_text(
    location: str = None,
    radius: int = 2400,
    api_key: str = None,
    keyword: str = None,
    page_token: str = None,
    location_restriction: dict = None,
) -> tuple:
    """
    Search for places using text search with pagination.
    Uses Places API (New) v1 searchText endpoint.
    
    Args:
        location: "lat,lng" string (used with locationBias circle if no restriction)
        radius: Search radius in meters
        api_key: API key
        keyword: Search keyword
        page_token: Next page token for pagination
        location_restriction: Optional rectangle dict for hard boundary
        
    Returns:
        Tuple of (list of place results, next_page_token)
    """
    url = f"{PLACES_API_BASE}/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key or GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.types,places.primaryType,places.location,nextPageToken"
    }
    
    body = {
        "textQuery": keyword or "restaurant",
        "maxResultCount": 20
    }
    
    if location_restriction:
        body["locationRestriction"] = location_restriction
    elif location:
        lat, lng = float(location.split(',')[0]), float(location.split(',')[1])
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius
            }
        }
    
    if page_token:
        body["pageToken"] = page_token
    
    response = requests.post(url, headers=headers, json=body, timeout=30)
    
    if response.status_code != 200:
        print(f"Text Search API Error: {response.status_code}")
        return [], None
    
    data = response.json()
    places = data.get('places', [])
    next_token = data.get('nextPageToken')
    
    return places, next_token


def search_places_paginated(
    location: str = None,
    radius: int = 2400,
    api_key: str = None,
    keyword: str = None,
    max_results: int = 60,
    location_restriction: dict = None,
) -> List[Dict]:
    """
    Search for places with full pagination support.
    Fetches multiple pages until max_results or no more pages.
    
    Args:
        location: "lat,lng" string
        radius: Search radius in meters
        api_key: API key
        keyword: Search keyword
        max_results: Maximum total results to fetch
        location_restriction: Optional rectangle dict for hard boundary
        
    Returns:
        List of all place results
    """
    api_key = api_key or GOOGLE_PLACES_API_KEY
    all_places = []
    page_token = None
    pages = 0
    max_pages = (max_results + 19) // 20
    
    while len(all_places) < max_results and pages < max_pages:
        places, page_token = search_places_text(
            location=location,
            radius=radius,
            api_key=api_key,
            keyword=keyword,
            page_token=page_token,
            location_restriction=location_restriction,
        )
        
        if not places:
            break
        
        all_places.extend(places)
        pages += 1
        
        if not page_token:
            break
        
        time.sleep(0.5)  # Avoid rate limiting
    
    return all_places[:max_results]


def calculate_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lng / 2) * math.sin(d_lng / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def filter_by_distance(places: List[Dict], center_lat: float, center_lng: float, 
                       max_distance: float) -> List[Dict]:
    """
    Filter places by distance from center point.
    
    Args:
        places: List of place dictionaries with location data
        center_lat: Center latitude
        center_lng: Center longitude
        max_distance: Maximum distance in meters
        
    Returns:
        Filtered list of places within max_distance
    """
    filtered = []
    for place in places:
        location = place.get('location', {})
        if not location:
            # If no location data, include it (conservative)
            filtered.append(place)
            continue
        
        place_lat = location.get('latitude')
        place_lng = location.get('longitude')
        
        if place_lat is None or place_lng is None:
            filtered.append(place)
            continue
        
        distance = calculate_distance_meters(center_lat, center_lng, place_lat, place_lng)
        
        if distance <= max_distance:
            filtered.append(place)
    
    return filtered


def fetch_all_places(location: str, radius: int = 800, api_key: str = None,
                     keywords: List[str] = None) -> List[Dict]:
    """
    Fetch all possible places using text search with pagination.
    Searches multiple keywords, deduplicates results, and filters by distance.
    
    Args:
        location: "lat,lng" string
        radius: Search radius in meters (default 800m = ~10 min walk)
        api_key: API key
        keywords: List of search keywords (default: restaurant, bar, happy hour, etc.)
        
    Returns:
        Combined list of unique place results within radius
    """
    api_key = api_key or GOOGLE_PLACES_API_KEY
    center_lat, center_lng = float(location.split(',')[0]), float(location.split(',')[1])
    all_places = {}
    
    if keywords is None:
        keywords = ["restaurant", "bar", "happy hour", "pub", "grill", "kitchen", "brewery"]
    
    print("=" * 60)
    print("FETCHING ALL PLACES (text search with pagination)")
    print("=" * 60)
    
    for keyword in keywords:
        print(f"\n[Searching] '{keyword}'")
        places = search_places_paginated(
            location, radius, api_key, 
            keyword=keyword, 
            max_results=60
        )
        
        for place in places:
            pid = place.get('id')
            if pid and pid not in all_places:
                all_places[pid] = place
        
        print(f"  Found {len(places)} places (total unique: {len(all_places)})")
    
    # Filter by distance
    print(f"\nFiltering by distance ({radius}m radius)...")
    places_list = list(all_places.values())
    filtered = filter_by_distance(places_list, center_lat, center_lng, radius)
    print(f"  Kept {len(filtered)}/{len(places_list)} places within {radius}m")
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL PLACES WITHIN {radius}m: {len(filtered)}")
    print(f"{'=' * 60}")
    
    return filtered


def convert_to_restaurant(place_data: Dict[str, Any]) -> Restaurant:
    """
    Convert Places API v1 response to Restaurant model.

    Args:
        place_data: API response for a single place

    Returns:
        Restaurant instance
    """
    name = place_data.get('displayName', {}).get('text', '')
    address = place_data.get('formattedAddress', '')
    phone = place_data.get('nationalPhoneNumber', '')
    website = place_data.get('websiteUri', '')

    # Parse regular opening hours
    regular_hours = ""
    reg_hours = place_data.get('regularOpeningHours', {})
    if reg_hours:
        descriptions = reg_hours.get('weekdayDescriptions', [])
        if descriptions:
            regular_hours = ' | '.join(descriptions)

    # Parse happy hours
    happy_hour_times = ""
    sec_hours = place_data.get('currentSecondaryOpeningHours', [])
    hh_result = parse_secondary_opening_hours(sec_hours)
    if hh_result:
        happy_hour_times = hh_result
        # Safe print for Windows console encoding
        try:
            print(f"    [OK] Happy hours: {hh_result[:60]}...")
        except UnicodeEncodeError:
            print("    [OK] Happy hours: <Unicode content>")

    source = 'Google Places API (Happy Hours)' if happy_hour_times else 'Google Places API'

    location = place_data.get('location', {})

    # Extract Google Maps URL
    google_maps_url = place_data.get('googleMapsUri', '')

    # Extract editorial summary (one-sentence description)
    generative_summary = ""
    summary_obj = place_data.get('editorialSummary', {})
    if summary_obj and isinstance(summary_obj, dict):
        generative_summary = summary_obj.get('text', '')

    return Restaurant(
        restaurant_name=name,
        address=address,
        phone_number=phone,
        website_url=website,
        happy_hour_times=happy_hour_times,
        regular_hours=regular_hours,
        rating=str(place_data.get('rating') or ''),
        review_count=str(place_data.get('userRatingCount') or ''),
        price_level=str(place_data.get('priceLevel') or ''),
        source=source,
        freshness_date='',
        latitude=str(location.get('latitude', '')) if location else '',
        longitude=str(location.get('longitude', '')) if location else '',
        place_id=place_data.get('id', ''),
        google_maps_url=google_maps_url,
        generative_summary=generative_summary
    )


def fetch_92116_restaurants(api_key: str = None, max_results: int = 200) -> List[Restaurant]:
    """
    Fetch restaurants in 92116 area with happy hour data.
    Uses text search with pagination to get around the 20-result limit.
    
    Args:
        api_key: Optional API key
        max_results: Maximum results to fetch
        
    Returns:
        List of Restaurant instances
    """
    api_key = api_key or GOOGLE_PLACES_API_KEY
    location = "32.762889,-117.119922"
    
    radius = 4000  # ~2.5 miles
    
    print(f"Fetching restaurants near {location}")
    print(f"Radius: {radius}m (~2.5 miles), Target: {max_results} places\n")
    
    # Fetch all places using pagination
    all_places = fetch_all_places(location, radius=radius, api_key=api_key)
    
    # Limit if needed
    if len(all_places) > max_results:
        print(f"\nLimiting to {max_results} places (found {len(all_places)})")
        all_places = all_places[:max_results]
    
    print(f"\nProcessing {len(all_places)} places for details...")
    
    restaurants = []
    hh_count = 0
    
    for i, place_summary in enumerate(all_places, 1):
        place_id = place_summary.get('id')
        name = place_summary.get('displayName', {}).get('text', 'Unknown')

        # Safe print for Windows console encoding
        try:
            print(f"[{i}/{len(all_places)}] {name}...")
        except UnicodeEncodeError:
            print(f"[{i}/{len(all_places)}] <Unicode name>...")

        details = get_place_details_new(place_id, api_key)
        if not details:
            continue

        try:
            restaurant = convert_to_restaurant(details)
            restaurants.append(restaurant)
            if restaurant.happy_hour_times:
                hh_count += 1
        except UnicodeEncodeError as e:
            print(f"    Error: Unicode encoding issue")
            continue
        except Exception as e:
            print(f"    Error: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"Total: {len(restaurants)} restaurants")
    print(f"With happy hours: {hh_count}")
    print(f"{'='*60}")
    
    return restaurants


if __name__ == '__main__':
    results = fetch_92116_restaurants()
    for r in results[:3]:
        print(f"\n{r.restaurant_name}:")
        print(f"  HH: {r.happy_hour_times or 'None'}")
