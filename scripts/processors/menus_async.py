"""
Async menu processor using AI to extract cheapest items.
"""
import asyncio
import re
from typing import Awaitable, Callable, Optional

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import AsyncOpenRouterClient
from ai.prompts import format_menu_prompt, format_menu_image_prompt
from storage import Restaurant
from fetchers.website import AsyncWebsiteFetcher
from parsers.content_parsers import parse_menu_response
from parsers.menu_text import focus_text_for_happy_hour_menu

# Pages with fewer than this many characters are considered image-only / empty
# and trigger a vision-based extraction attempt if menu images are found.
_IMAGE_ONLY_THRESHOLD = 300


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

        # Remember the first URL so we can check it for images later.
        first_menu_url = menu_url

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
            # Last-ditch effort: if the original priority URL had a happy-hour
            # image, try to extract menu data from the image via vision AI.
            image_urls = await self.fetcher.afetch_menu_images(first_menu_url)
            if image_urls and hasattr(self.ai, 'acomplete_with_images'):
                try:
                    print(f"  No text content — trying vision extraction from {len(image_urls)} image(s)")
                    vision_prompt = format_menu_image_prompt(
                        restaurant.restaurant_name,
                        happy_hour_times=restaurant.happy_hour_times or None,
                    )
                    response = await self.ai.acomplete_with_images(
                        prompt=vision_prompt,
                        image_urls=image_urls,
                        system="You are a menu parser. Extract happy hour items from the image. Return JSON only.",
                    )
                    result = parse_menu_response(response)
                    drink = result.get('drink')
                    food = result.get('food')
                    if drink:
                        restaurant.cheapest_drink = drink.get('name', '')
                        restaurant.cheapest_drink_price = drink.get('price')
                    if food:
                        restaurant.cheapest_food = food.get('name', '')
                        restaurant.cheapest_food_price = food.get('price')
                    restaurant.menu_summary = result.get('short_summary', '') if (drink or food) else ''
                    if drink or food:
                        if drink:
                            print(f"  [OK] Drink (vision): {restaurant.cheapest_drink}")
                        if food:
                            print(f"  [OK] Food (vision): {restaurant.cheapest_food}")
                        return True
                except Exception as e:
                    print(f"  Vision extraction failed: {e}")
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

            # Validate results against original text.
            # Use token-based matching: at least one significant word (>3 chars)
            # from the item name must appear in the text to guard against
            # hallucinations while tolerating minor phrasing differences.
            drink = result.get('drink')
            food = result.get('food')

            def _item_in_text(item_name: str, haystack: str) -> bool:
                """Return True if the item name has meaningful overlap with haystack."""
                # Strip price tokens and lowercase
                cleaned = re.sub(r'\$[\d.]+', '', item_name).strip().lower()
                if not cleaned:
                    return False
                haystack_lower = haystack.lower()
                # First try exact match of the cleaned full name
                if cleaned in haystack_lower:
                    return True
                # Fall back: check if at least one significant word appears
                _STOP = {'the', 'and', 'with', 'for', 'from', 'a', 'an', 'in',
                         'of', 'or', 'on', 'at', 'to', 'by', 'is', 'it'}
                words = [w for w in re.split(r'\W+', cleaned) if len(w) > 3 and w not in _STOP]
                if not words:
                    # All words are short/stop-words — fall back to exact match only
                    return cleaned in haystack_lower
                return any(w in haystack_lower for w in words)

            if drink and drink.get('name'):
                drink_name = drink.get('name', '')
                if not _item_in_text(drink_name, text):
                    print(f"  Drink '{drink_name}' not found in text, rejecting")
                    drink = None

            if food and food.get('name'):
                food_name = food.get('name', '')
                if not _item_in_text(food_name, text):
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
                # Text extraction found nothing. If the original menu URL was
                # short (likely image-only), try vision extraction as a fallback.
                if (
                    not drink and not food
                    and first_menu_url != menu_url
                    and hasattr(self.ai, 'acomplete_with_images')
                ):
                    image_urls = await self.fetcher.afetch_menu_images(first_menu_url)
                    if image_urls:
                        try:
                            print(f"  Text found nothing — trying vision extraction from {len(image_urls)} image(s)")
                            vision_prompt = format_menu_image_prompt(
                                restaurant.restaurant_name,
                                happy_hour_times=restaurant.happy_hour_times or None,
                            )
                            v_response = await self.ai.acomplete_with_images(
                                prompt=vision_prompt,
                                image_urls=image_urls,
                                system="You are a menu parser. Extract happy hour items from the image. Return JSON only.",
                            )
                            v_result = parse_menu_response(v_response)
                            v_drink = v_result.get('drink')
                            v_food = v_result.get('food')
                            if v_drink:
                                restaurant.cheapest_drink = v_drink.get('name', '')
                                restaurant.cheapest_drink_price = v_drink.get('price')
                            if v_food:
                                restaurant.cheapest_food = v_food.get('name', '')
                                restaurant.cheapest_food_price = v_food.get('price')
                            restaurant.menu_summary = v_result.get('short_summary', '') if (v_drink or v_food) else ''
                            if v_drink or v_food:
                                if v_drink:
                                    print(f"  [OK] Drink (vision fallback): {restaurant.cheapest_drink}")
                                if v_food:
                                    print(f"  [OK] Food (vision fallback): {restaurant.cheapest_food}")
                                return True
                        except Exception as e:
                            print(f"  Vision fallback failed: {e}")

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
        per_task_timeout: Optional[float] = None,
        checkpoint_every: int = 0,
        checkpoint_callback: Optional[Callable[[int, int], Awaitable[None]]] = None,
    ) -> list:
        """Process multiple restaurants concurrently."""
        total = len(restaurants)
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def process_one(restaurant: Restaurant) -> bool:
            nonlocal completed
            async with semaphore:
                try:
                    if per_task_timeout is not None and per_task_timeout > 0:
                        result = await asyncio.wait_for(
                            self.process(restaurant),
                            timeout=per_task_timeout,
                        )
                    else:
                        result = await self.process(restaurant)
                except asyncio.TimeoutError:
                    try:
                        nm = restaurant.restaurant_name
                    except UnicodeEncodeError:
                        nm = "<Unicode name>"
                    try:
                        print(f"\n  Task timeout ({per_task_timeout}s): {nm}")
                    except UnicodeEncodeError:
                        print(f"\n  Task timeout ({per_task_timeout}s): <Unicode name>")
                    result = False
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                if (
                    checkpoint_every > 0
                    and checkpoint_callback
                    and completed % checkpoint_every == 0
                ):
                    await checkpoint_callback(completed, total)
                return result

        tasks = [process_one(r) for r in restaurants]
        await asyncio.gather(*tasks)
        return restaurants
