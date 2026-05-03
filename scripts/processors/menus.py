"""
Menu processor using AI to extract cheapest items.
"""
import re
from typing import Optional

from ai import OpenRouterClient
from ai.prompts import format_menu_prompt
from storage import Restaurant
from fetchers.website import WebsiteFetcher
from parsers.content_parsers import parse_menu_response
from parsers.menu_text import focus_text_for_happy_hour_menu


class MenuProcessor:
    """Process restaurant websites to extract menu deals."""
    
    def __init__(self, ai_client: OpenRouterClient, fetcher: Optional[WebsiteFetcher] = None):
        self.ai = ai_client
        self.fetcher = fetcher or WebsiteFetcher()
    
    def process(self, restaurant: Restaurant) -> bool:
        """
        Extract menu data for a restaurant.
        
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
        
        # Reject if content is too short (likely error/loading page)
        if len(text) < 100:
            print(f"  Content too short ({len(text)} chars), likely error page")
            return False

        text = focus_text_for_happy_hour_menu(text)

        # Send to AI
        try:
            prompt = format_menu_prompt(
                restaurant.restaurant_name,
                text,
                happy_hour_times=restaurant.happy_hour_times or None,
            )
            response = self.ai.complete(
                prompt=prompt,
                system="You are a menu parser. ONLY extract items explicitly listed in the text. DO NOT make up items. Return JSON only."
            )
            
            # Parse response
            result = parse_menu_response(response)
            
            # Validate results against original text
            drink = result.get('drink')
            food = result.get('food')
            
            # Check if items are actually in the original text
            if drink and drink.get('name'):
                drink_name = drink.get('name', '').lower()
                # Extract just the item name without price for matching
                drink_item = re.sub(r'\$[\d.]+', '', drink_name).strip()
                if drink_item and drink_item not in text.lower():
                    print(f"  Drink '{drink_name}' not found in text, rejecting")
                    drink = None
            
            if food and food.get('name'):
                food_name = food.get('name', '').lower()
                # Extract just the item name without price for matching
                food_item = re.sub(r'\$[\d.]+', '', food_name).strip()
                if food_item and food_item not in text.lower():
                    print(f"  Food '{food_name}' not found in text, rejecting")
                    food = None
            
            # Update restaurant only with validated items
            if drink:
                restaurant.cheapest_drink = drink.get('name', '')
                restaurant.cheapest_drink_price = drink.get('price')
            
            if food:
                restaurant.cheapest_food = food.get('name', '')
                restaurant.cheapest_food_price = food.get('price')
            
            restaurant.menu_summary = result.get('short_summary', '') if (drink or food) else ''
            
            if drink or food:
                if drink:
                    print(f"  [OK] Drink: {restaurant.cheapest_drink}")
                if food:
                    print(f"  [OK] Food: {restaurant.cheapest_food}")
                return True
            else:
                print(f"  No valid menu data found")
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
