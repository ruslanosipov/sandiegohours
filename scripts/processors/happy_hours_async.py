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
from ai.prompts import format_happy_hour_image_prompt, format_happy_hour_prompt
from storage import Restaurant
from fetchers.website import AsyncWebsiteFetcher, homepage_fallback_urls
from parsers.content_parsers import parse_happy_hour_response, format_happy_hour_times


_MIN_USABLE_TEXT = 300


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
        first_menu_url = menu_url
        try:
            print(f"  URL: {menu_url}")
        except UnicodeEncodeError:
            print("  URL: <Unicode content>")

        # Fetch and clean content
        text = await self.fetcher.afetch_clean(menu_url)
        if not text or len(text) < _MIN_USABLE_TEXT:
            for candidate in homepage_fallback_urls(restaurant.website_url):
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
                    if len(text) >= _MIN_USABLE_TEXT:
                        break

        if not text:
            if await self._try_vision_schedule(restaurant, first_menu_url):
                return True
            print(f"  Failed to fetch content")
            return False

        try:
            print(f"  Fetched {len(text)} chars of content from {menu_url}")
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
                if await self._try_vision_schedule(restaurant, first_menu_url):
                    return True
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

    async def _try_vision_schedule(self, restaurant: Restaurant, url: str) -> bool:
        """Try extracting a happy-hour schedule from menu/special image URLs."""
        if not url or not hasattr(self.ai, 'acomplete_with_images'):
            return False

        image_urls = await self.fetcher.afetch_menu_images(url)
        if not image_urls:
            return False

        try:
            print(f"  Trying vision schedule extraction from {len(image_urls)} image(s)")
            response = await self.ai.acomplete_with_images(
                prompt=format_happy_hour_image_prompt(restaurant.restaurant_name),
                image_urls=image_urls,
                system="You are a happy hour schedule parser. Extract structured data from images. Return JSON only.",
            )
            result = parse_happy_hour_response(response)
            confidence = result.get('confidence', 'low')
            if confidence in ['low', 'none'] or not result['happy_hours']:
                print(f"  Vision schedule low confidence ({confidence}), skipping")
                return False

            restaurant.happy_hour_times = format_happy_hour_times(result['happy_hours'])
            restaurant.source = f'Website image (AI parsed, {confidence} confidence)'
            try:
                print(f"  [OK] Found from image: {restaurant.happy_hour_times[:60]}...")
            except UnicodeEncodeError:
                print("  [OK] Found happy hours from image")
            return True
        except Exception as e:
            print(f"  Vision schedule extraction failed: {e}")
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
