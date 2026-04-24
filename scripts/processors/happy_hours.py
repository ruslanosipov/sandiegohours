"""
Happy hour schedule processor using AI.
"""
from typing import Optional

from ai import OpenRouterClient
from ai.prompts import format_happy_hour_prompt
from storage import Restaurant
from fetchers.website import WebsiteFetcher
from parsers.content_parsers import parse_happy_hour_response, format_happy_hour_times


class HappyHourProcessor:
    """Process restaurant websites to extract happy hour schedules."""
    
    def __init__(self, ai_client: OpenRouterClient, fetcher: Optional[WebsiteFetcher] = None):
        self.ai = ai_client
        self.fetcher = fetcher or WebsiteFetcher()
    
    def process(self, restaurant: Restaurant) -> bool:
        """
        Extract happy hour times for a restaurant.
        
        Args:
            restaurant: Restaurant to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            name = restaurant.restaurant_name
        except UnicodeEncodeError:
            name = "<Unicode name>"
        
        if not restaurant.website_url:
            try:
                print(f"  No website for {name}")
            except UnicodeEncodeError:
                print("  No website for <Unicode name>")
            return False
        
        try:
            print(f"Processing {name}...")
        except UnicodeEncodeError:
            print("Processing <Unicode name>...")
        
        # Find menu/happy hour page
        menu_url = self.fetcher.find_menu_page(restaurant.website_url)
        try:
            print(f"  URL: {menu_url}")
        except UnicodeEncodeError:
            print("  URL: <Unicode content>")
        
        # Fetch and clean content
        text = self.fetcher.fetch_clean(menu_url)
        if not text:
            print(f"  Failed to fetch content")
            return False
        
        try:
            print(f"  Fetched {len(text)} chars of content")
        except UnicodeEncodeError:
            print("  Fetched content")
        
        # Send to AI
        try:
            prompt = format_happy_hour_prompt(text)
            response = self.ai.complete(
                prompt=prompt,
                system="You are a happy hour schedule parser. Extract structured data from website content. Return JSON only."
            )
            
            # Parse response
            result = parse_happy_hour_response(response)
            
            # Check confidence level
            confidence = result.get('confidence', 'low')
            if confidence in ['low', 'none']:
                print(f"  Low confidence ({confidence}), skipping")
                return False
            
            if result['happy_hours']:
                # Update restaurant
                restaurant.happy_hour_times = format_happy_hour_times(result['happy_hours'])
                restaurant.source = f'Website (AI parsed, {confidence} confidence)'
                try:
                    print(f"  [OK] Found: {restaurant.happy_hour_times[:60]}...")
                except UnicodeEncodeError:
                    print("  [OK] Found happy hours")
                return True
            else:
                print(f"  No happy hours found")
                return False
                
        except Exception as e:
            print(f"  AI error: {e}")
            return False
    
    def process_batch(self, restaurants: list, progress_callback=None) -> list:
        """
        Process multiple restaurants.
        
        Args:
            restaurants: List of restaurants
            progress_callback: Optional callback(current, total)
            
        Returns:
            Updated list of restaurants
        """
        total = len(restaurants)
        
        for i, restaurant in enumerate(restaurants):
            if progress_callback:
                progress_callback(i + 1, total)
            
            self.process(restaurant)
        
        return restaurants
