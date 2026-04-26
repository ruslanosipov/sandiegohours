"""
Async happy hour schedule processor using AI.
"""
import asyncio
from typing import Optional

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import AsyncOpenRouterClient
from ai.prompts import format_happy_hour_prompt
from storage import Restaurant
from fetchers.website import AsyncWebsiteFetcher
from parsers.content_parsers import parse_happy_hour_response, format_happy_hour_times


class AsyncHappyHourProcessor:
    """Async processor for extracting happy hour schedules from restaurant websites."""

    def __init__(
        self,
        ai_client: AsyncOpenRouterClient,
        fetcher: Optional[AsyncWebsiteFetcher] = None,
    ):
        self.ai = ai_client
        self.fetcher = fetcher or AsyncWebsiteFetcher()

    async def process(self, restaurant: Restaurant) -> bool:
        """Extract happy hour times for a single restaurant."""
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
            response = await self.ai.acomplete(
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
