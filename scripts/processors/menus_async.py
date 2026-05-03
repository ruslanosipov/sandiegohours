"""
Async menu processor using AI to extract cheapest items.
"""
import asyncio
import re
from typing import Optional

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import AsyncOpenRouterClient
from ai.prompts import format_menu_prompt
from storage import Restaurant
from fetchers.website import AsyncWebsiteFetcher
from parsers.content_parsers import parse_menu_response
from parsers.menu_text import focus_text_for_happy_hour_menu


class AsyncMenuProcessor:
    """Async processor for extracting menu deals from restaurant websites."""

    def __init__(
        self,
        ai_client: AsyncOpenRouterClient,
        fetcher: Optional[AsyncWebsiteFetcher] = None,
    ):
        self.ai = ai_client
        self.fetcher = fetcher or AsyncWebsiteFetcher()

    async def process(self, restaurant: Restaurant) -> bool:
        """Extract menu data for a single restaurant."""
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

        # Find menu/happy hour page (checks priority paths concurrently)
        menu_url = await self.fetcher.afind_menu_page(restaurant.website_url)
        try:
            print(f"  URL: {menu_url}")
        except UnicodeEncodeError:
            print("  URL: <Unicode content>")

        # Fetch and clean content
        text = await self.fetcher.afetch_clean(menu_url)

        # Fallback: some sites' priority paths (e.g. /happyhour) are image-only
        # graphic pages while the real menu content lives on the home page or
        # at /home (common with Wix sites). If the chosen URL yields too little
        # usable text, retry on the homepage variants.
        MIN_USABLE = 300
        if not text or len(text) < MIN_USABLE:
            base = restaurant.website_url.rstrip('/')
            for candidate in (f"{base}/home", f"{base}/"):
                if candidate == menu_url or candidate.rstrip('/') == menu_url.rstrip('/'):
                    continue
                try:
                    print(f"  Retrying on homepage: {candidate}")
                except UnicodeEncodeError:
                    print("  Retrying on homepage")
                fallback = await self.fetcher.afetch_clean(candidate)
                if fallback and len(fallback) > len(text or ""):
                    text = fallback
                    menu_url = candidate
                    if len(text) >= MIN_USABLE:
                        break

        if not text:
            print(f"  Failed to fetch content")
            return False

        try:
            print(f"  Fetched {len(text)} chars of content from {menu_url}")
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
            response = await self.ai.acomplete(
                prompt=prompt,
                system="You are a menu parser. ONLY extract items explicitly listed in the text. DO NOT make up items. Return JSON only."
            )

            # Parse response
            result = parse_menu_response(response)

            # Validate results against original text
            drink = result.get('drink')
            food = result.get('food')

            if drink and drink.get('name'):
                drink_name = drink.get('name', '').lower()
                drink_item = re.sub(r'\$[\d.]+', '', drink_name).strip()
                if drink_item and drink_item not in text.lower():
                    print(f"  Drink '{drink_name}' not found in text, rejecting")
                    drink = None

            if food and food.get('name'):
                food_name = food.get('name', '').lower()
                food_item = re.sub(r'\$[\d.]+', '', food_name).strip()
                if food_item and food_item not in text.lower():
                    print(f"  Food '{food_name}' not found in text, rejecting")
                    food = None

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

    async def process_batch(
        self,
        restaurants: list,
        concurrency: int = 20,
        progress_callback=None,
    ) -> list:
        """Process multiple restaurants concurrently."""
        total = len(restaurants)
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def process_one(idx: int, restaurant: Restaurant) -> bool:
            nonlocal completed
            async with semaphore:
                result = await self.process(restaurant)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                return result

        tasks = [process_one(i, r) for i, r in enumerate(restaurants)]
        await asyncio.gather(*tasks)
        return restaurants
