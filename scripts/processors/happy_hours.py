"""
Happy hour schedule processor using AI.
"""
from typing import Optional

from scripts.ai import OpenRouterClient
from scripts.ai.prompts import format_happy_hour_prompt
from scripts.storage import Restaurant
from scripts.fetchers.website import WebsiteFetcher
from scripts.parsers.content_parsers import parse_happy_hour_response, format_happy_hour_times


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
        if not restaurant.website_url:
            print(f"  No website for {restaurant.restaurant_name}")
            return False
        
        print(f"Processing {restaurant.restaurant_name}...")
        
        # Find menu/happy hour page
        menu_url = self.fetcher.find_menu_page(restaurant.website_url)
        print(f"  URL: {menu_url}")
        
        # Fetch and clean content
        text = self.fetcher.fetch_clean(menu_url)
        if not text:
            print(f"  Failed to fetch content")
            return False
        
        print(f"  Fetched {len(text)} chars of content")
        
        # Send to AI
        try:
            prompt = format_happy_hour_prompt(text)
            response = self.ai.complete(
                prompt=prompt,
                system="You are a happy hour schedule parser. Extract structured data from website content. Return JSON only."
            )
            
            # Parse response
            result = parse_happy_hour_response(response)
            
            if result['happy_hours']:
                # Update restaurant
                restaurant.happy_hour_times = format_happy_hour_times(result['happy_hours'])
                restaurant.source = 'Website (AI parsed)'
                print(f"  ✓ Found: {restaurant.happy_hour_times[:60]}...")
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
