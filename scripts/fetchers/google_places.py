"""
Google Places API fetcher for restaurant data.
"""
import requests
from typing import List, Optional, Dict, Any

from storage import Restaurant

GOOGLE_PLACES_API_KEY = "AIzaSyCEsrQU4JQp_pOoLDOHA9GsUaOb5RoxKWk"
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_API_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GooglePlacesFetcher:
    """Fetch restaurant data from Google Places API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GOOGLE_PLACES_API_KEY
    
    def search_nearby(
        self, 
        location: str,
        radius: int = 1500,
        place_type: str = "restaurant|bar"
    ) -> List[Dict[str, Any]]:
        """
        Search for restaurants/bars near a location.
        
        Args:
            location: "lat,lng" string
            radius: Search radius in meters
            place_type: Types of places to search
            
        Returns:
            List of place results
        """
        params = {
            'location': location,
            'radius': radius,
            'type': place_type,
            'key': self.api_key
        }
        
        response = requests.get(PLACES_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') != 'OK':
            error_msg = data.get('error_message', data.get('status', 'Unknown error'))
            raise Exception(f"Places API error: {error_msg}")
        
        return data.get('results', [])
    
    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a place.
        
        Args:
            place_id: Google place_id
            
        Returns:
            Place details
        """
        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,website,opening_hours,secondary_opening_hours,price_level,rating,user_ratings_total',
            'key': self.api_key
        }
        
        response = requests.get(DETAILS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') != 'OK':
            error_msg = data.get('error_message', data.get('status', 'Unknown error'))
            raise Exception(f"Places Details API error: {error_msg}")
        
        return data.get('result', {})
    
    def convert_to_restaurant(self, place: Dict[str, Any], details: Dict[str, Any] = None) -> Restaurant:
        """
        Convert Google Places result to Restaurant model.
        
        Args:
            place: Places API result
            details: Optional detailed result
            
        Returns:
            Restaurant instance
        """
        # Use details if available, otherwise use basic place data
        source = details or place
        
        # Format opening hours
        opening_hours = ""
        if source.get('opening_hours', {}).get('weekday_text'):
            hours = source['opening_hours']['weekday_text']
            opening_hours = ' | '.join(hours)
        
        # Format happy hours from secondary_opening_hours
        happy_hour_times = ""
        secondary_hours = source.get('secondary_opening_hours', {})
        if secondary_hours and secondary_hours.get('weekday_text'):
            hh_list = secondary_hours['weekday_text']
            happy_hour_times = ' | '.join(hh_list)
            print(f"    Found happy hours: {happy_hour_times[:60]}...")
        
        # Extract location for coordinates
        location = source.get('geometry', {}).get('location', {})
        
        return Restaurant(
            restaurant_name=source.get('name', ''),
            address=source.get('formatted_address') or source.get('vicinity', ''),
            phone_number=source.get('formatted_phone_number', ''),
            website_url=source.get('website', ''),
            happy_hour_times=happy_hour_times,
            regular_hours=opening_hours,
            rating=str(source.get('rating', '')),
            review_count=str(source.get('user_ratings_total', '')),
            price_level=str(source.get('price_level', '')),
            source='Google Maps API',
            freshness_date='',  # Will be set by orchestrator
            latitude=str(location.get('lat', '')) if location else '',
            longitude=str(location.get('lng', '')) if location else ''
        )
    
    def fetch_area(
        self,
        location: str,
        radius: int = 1500,
        max_results: int = 60
    ) -> List[Restaurant]:
        """
        Fetch all restaurants in an area.
        
        Args:
            location: "lat,lng" string
            radius: Search radius in meters
            max_results: Maximum results (Google limits to 60)
            
        Returns:
            List of Restaurant instances
        """
        restaurants = []
        next_page_token = None
        
        print(f"Fetching restaurants near {location} (radius: {radius}m)")
        
        while len(restaurants) < max_results:
            params = {
                'location': location,
                'radius': radius,
                'type': 'restaurant|bar',
                'key': self.api_key
            }
            
            if next_page_token:
                params['pagetoken'] = next_page_token
            
            response = requests.get(PLACES_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') not in ['OK', 'ZERO_RESULTS']:
                error_msg = data.get('error_message', data.get('status'))
                raise Exception(f"Places API error: {error_msg}")
            
            results = data.get('results', [])
            print(f"  Found {len(results)} places in this page")
            
            for place in results:
                # Get detailed info
                try:
                    details = self.get_place_details(place['place_id'])
                    restaurant = self.convert_to_restaurant(place, details)
                    restaurants.append(restaurant)
                except Exception as e:
                    print(f"  Error fetching details for {place.get('name')}: {e}")
                    # Use basic data
                    restaurant = self.convert_to_restaurant(place)
                    restaurants.append(restaurant)
            
            # Check for next page
            next_page_token = data.get('next_page_token')
            if not next_page_token:
                break
            
            # Google requires delay between page requests
            import time
            time.sleep(2)
        
        print(f"Total: {len(restaurants)} restaurants")
        return restaurants[:max_results]


def fetch_92116_restaurants() -> List[Restaurant]:
    """
    Fetch restaurants in 92116 area (Normal Heights).
    Center point: 2861 Copley Ave, San Diego, CA 92116
    """
    # Coordinates for 2861 Copley Ave
    location = "32.762889,-117.119922"
    
    fetcher = GooglePlacesFetcher()
    return fetcher.fetch_area(location, radius=1500, max_results=60)
