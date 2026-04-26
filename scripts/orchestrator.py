#!/usr/bin/env python3
"""
Main orchestrator for happy hour data pipeline (async / parallel).

Usage:
    python orchestrator.py --full                    # Run full pipeline
    python orchestrator.py --step=parse_menus        # Resume from specific step
    python orchestrator.py --step=parse_happy_hours  # Run only happy hour parser
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from storage import CSVManager, Restaurant, ProcessingState
from ai import OpenRouterClient
from ai.openrouter import AsyncOpenRouterClient
from fetchers import WebsiteFetcher
from fetchers.website import AsyncWebsiteFetcher
from fetchers.google_places import fetch_92116_restaurants
from fetchers.google_places_async import AsyncGooglePlacesFetcher
from processors import HappyHourProcessor, MenuProcessor
from processors.happy_hours_async import AsyncHappyHourProcessor
from processors.menus_async import AsyncMenuProcessor


# Configuration
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DATA_DIR = Path(__file__).parent.parent / 'public'
CACHE_DIR = Path(__file__).parent.parent / '.cache'
PROGRESS_FILE = CACHE_DIR / 'progress.json'

# Concurrency tunables
GOOGLE_PLACES_CONCURRENCY = 10
OPENROUTER_CONCURRENCY = 30
WEBSITE_FETCH_DELAY = 0.2
WEBSITE_FETCH_CONCURRENCY = 5

# CLI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def load_progress() -> Optional[ProcessingState]:
    """Load previous progress if exists."""
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text())
            return ProcessingState.from_dict(data)
        except Exception as e:
            print(f"{YELLOW}Warning: Could not load progress: {e}{RESET}")
    return None


def save_progress(state: ProcessingState):
    """Save current progress."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(state.to_dict(), indent=2))


def print_step(step_name: str):
    """Print formatted step header."""
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Sync fallbacks (kept for compatibility / testing)
# ---------------------------------------------------------------------------

def step_fetch_restaurants(storage: CSVManager) -> list:
    """Fetch restaurants from Google Places API or load from CSV."""
    print_step("Fetch Restaurants from Google Places")
    csv_path = DATA_DIR / 'happy_hours.csv'
    if csv_path.exists():
        print(f"Found existing {csv_path}")
        print("Refreshing from Google Places API (using --full)...")

    print("Fetching from Google Places API...")
    try:
        restaurants = fetch_92116_restaurants()
        for r in restaurants:
            r.freshness_date = datetime.now().isoformat()[:10]
        storage.write('happy_hours.csv', restaurants)
        print(f"Saved {len(restaurants)} restaurants to happy_hours.csv")
        return restaurants
    except Exception as e:
        print(f"{RED}Error fetching from API: {e}{RESET}")
        print("Falling back to CSV...")
        restaurants = storage.read('happy_hours.csv', Restaurant)
        print(f"Loaded {len(restaurants)} restaurants")
        return restaurants


def step_apply_overrides(restaurants: list, storage: CSVManager) -> list:
    """Apply manual overrides from CSV."""
    print_step("Apply Manual Overrides")
    override_file = DATA_DIR / 'manual_overrides.csv'
    if not override_file.exists():
        print("No manual_overrides.csv found, skipping")
        return restaurants

    import csv
    overrides = {}
    with open(override_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('restaurant_name', '').strip()
            if name:
                overrides[name] = row

    print(f"Loaded {len(overrides)} overrides")
    applied = 0
    for r in restaurants:
        if r.restaurant_name in overrides:
            o = overrides[r.restaurant_name]
            if o.get('happy_hour_times'):
                r.happy_hour_times = o['happy_hour_times']
                r.source = 'Manual Override'
                applied += 1
                print(f"  Applied override for {r.restaurant_name}")

    print(f"\n{GREEN}Applied {applied} overrides{RESET}")
    return restaurants


def step_parse_happy_hours(restaurants: list, storage: CSVManager) -> list:
    """Parse happy hours from websites."""
    print_step("Parse Happy Hours from Websites")
    to_process = [r for r in restaurants if not r.happy_hour_times]
    print(f"Processing {len(to_process)} restaurants without happy hour data\n")

    ai = OpenRouterClient(API_KEY)
    fetcher = WebsiteFetcher(delay=1.0, cache_dir=CACHE_DIR / 'websites')
    processor = HappyHourProcessor(ai, fetcher)

    success_count = 0
    for i, restaurant in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] ", end="")
        if processor.process(restaurant):
            success_count += 1
        print()

    print(f"\n{GREEN}Success: {success_count}/{len(to_process)}{RESET}")
    storage.write('happy_hours.csv', restaurants)
    print(f"Saved to happy_hours.csv")
    return restaurants


def step_parse_menus(restaurants: list, storage: CSVManager) -> list:
    """Parse menu data from websites."""
    print_step("Parse Menus")
    to_process = [r for r in restaurants if not r.menu_summary and r.website_url]
    print(f"Processing {len(to_process)} restaurants without menu data\n")

    ai = OpenRouterClient(API_KEY)
    fetcher = WebsiteFetcher(delay=1.0, cache_dir=CACHE_DIR / 'websites')
    processor = MenuProcessor(ai, fetcher)

    success_count = 0
    for i, restaurant in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] ", end="")
        if processor.process(restaurant):
            success_count += 1
        print()

    print(f"\n{GREEN}Success: {success_count}/{len(to_process)}{RESET}")

    menu_data = [
        {
            'restaurant_name': r.restaurant_name,
            'cheapest_drink': r.cheapest_drink or '',
            'cheapest_drink_price': str(r.cheapest_drink_price or ''),
            'cheapest_food': r.cheapest_food or '',
            'cheapest_food_price': str(r.cheapest_food_price or ''),
            'menu_summary': r.menu_summary or ''
        }
        for r in restaurants if r.menu_summary
    ]

    if menu_data:
        storage.write_dicts('menu_data.csv', menu_data, [
            'restaurant_name', 'cheapest_drink', 'cheapest_drink_price',
            'cheapest_food', 'cheapest_food_price', 'menu_summary'
        ])
        print(f"Saved {len(menu_data)} menu records to menu_data.csv")

    return restaurants


def step_generate_summary(restaurants: list):
    """Print pipeline summary."""
    print_step("Summary")
    hh_count = sum(1 for r in restaurants if r.happy_hour_times)
    menu_count = sum(1 for r in restaurants if r.menu_summary)

    print(f"Total restaurants: {len(restaurants)}")
    print(f"With happy hours: {hh_count} ({hh_count/len(restaurants)*100:.1f}%)")
    print(f"With menu data: {menu_count} ({menu_count/len(restaurants)*100:.1f}%)")

    print("\nSample results:")
    for r in restaurants[:5]:
        if r.menu_summary:
            print(f"  {r.restaurant_name}: {r.menu_summary}")


# ---------------------------------------------------------------------------
# Async pipeline (highly parallel)
# ---------------------------------------------------------------------------

async def async_step_fetch_restaurants(storage: CSVManager) -> list:
    """Fetch restaurants using async Google Places API."""
    print_step("Fetch Restaurants from Google Places (Async)")
    csv_path = DATA_DIR / 'happy_hours.csv'
    if csv_path.exists():
        print(f"Found existing {csv_path}")
        print("Refreshing from Google Places API (using --full)...")

    print("Fetching from Google Places API...")
    try:
        async with AsyncGooglePlacesFetcher(
            api_key=os.environ.get("GOOGLE_PLACES_API_KEY", ""),
            details_concurrency=GOOGLE_PLACES_CONCURRENCY,
        ) as fetcher:
            restaurants = await fetcher.fetch_restaurants()

        for r in restaurants:
            r.freshness_date = datetime.now().isoformat()[:10]

        storage.write('happy_hours.csv', restaurants)
        print(f"Saved {len(restaurants)} restaurants to happy_hours.csv")
        return restaurants
    except Exception as e:
        print(f"{RED}Error fetching from API: {e}{RESET}")
        print("Falling back to CSV...")
        restaurants = storage.read('happy_hours.csv', Restaurant)
        print(f"Loaded {len(restaurants)} restaurants")
        return restaurants


async def async_step_parse_happy_hours(restaurants: list, storage: CSVManager) -> list:
    """Parse happy hours concurrently using AI."""
    print_step("Parse Happy Hours from Websites (Async)")
    to_process = [r for r in restaurants if not r.happy_hour_times]
    print(f"Processing {len(to_process)} restaurants without happy hour data\n")

    async with AsyncOpenRouterClient(
        API_KEY, max_concurrent=OPENROUTER_CONCURRENCY
    ) as ai, AsyncWebsiteFetcher(
        delay=WEBSITE_FETCH_DELAY,
        cache_dir=CACHE_DIR / 'websites',
        max_concurrent_fetches=WEBSITE_FETCH_CONCURRENCY,
    ) as fetcher:
        processor = AsyncHappyHourProcessor(ai, fetcher)

        success_count = 0
        def progress(current, total):
            nonlocal success_count
            # success_count is tracked inside process_one via return value,
            # but we can't easily get it from the callback. We'll count after.
            pass

        await processor.process_batch(
            to_process,
            concurrency=OPENROUTER_CONCURRENCY,
            progress_callback=lambda c, t: print(f"[{c}/{t}] processed", end="\r"),
        )

    success_count = sum(1 for r in to_process if r.happy_hour_times)
    print(f"\n{GREEN}Success: {success_count}/{len(to_process)}{RESET}")
    storage.write('happy_hours.csv', restaurants)
    print(f"Saved to happy_hours.csv")
    return restaurants


async def async_step_parse_menus(restaurants: list, storage: CSVManager) -> list:
    """Parse menus concurrently using AI."""
    print_step("Parse Menus (Async)")
    to_process = [r for r in restaurants if not r.menu_summary and r.website_url]
    print(f"Processing {len(to_process)} restaurants without menu data\n")

    async with AsyncOpenRouterClient(
        API_KEY, max_concurrent=OPENROUTER_CONCURRENCY
    ) as ai, AsyncWebsiteFetcher(
        delay=WEBSITE_FETCH_DELAY,
        cache_dir=CACHE_DIR / 'websites',
        max_concurrent_fetches=WEBSITE_FETCH_CONCURRENCY,
    ) as fetcher:
        processor = AsyncMenuProcessor(ai, fetcher)

        await processor.process_batch(
            to_process,
            concurrency=OPENROUTER_CONCURRENCY,
            progress_callback=lambda c, t: print(f"[{c}/{t}] processed", end="\r"),
        )

    success_count = sum(1 for r in to_process if r.menu_summary)
    print(f"\n{GREEN}Success: {success_count}/{len(to_process)}{RESET}")

    menu_data = [
        {
            'restaurant_name': r.restaurant_name,
            'cheapest_drink': r.cheapest_drink or '',
            'cheapest_drink_price': str(r.cheapest_drink_price or ''),
            'cheapest_food': r.cheapest_food or '',
            'cheapest_food_price': str(r.cheapest_food_price or ''),
            'menu_summary': r.menu_summary or ''
        }
        for r in restaurants if r.menu_summary
    ]

    if menu_data:
        storage.write_dicts('menu_data.csv', menu_data, [
            'restaurant_name', 'cheapest_drink', 'cheapest_drink_price',
            'cheapest_food', 'cheapest_food_price', 'menu_summary'
        ])
        print(f"Saved {len(menu_data)} menu records to menu_data.csv")

    return restaurants


# ---------------------------------------------------------------------------
# Orchestrator entry point
# ---------------------------------------------------------------------------

async def run_pipeline_async(start_step: str = 'load', resume: bool = False):
    """Run the full async processing pipeline."""
    storage = CSVManager(DATA_DIR)

    progress = load_progress() if resume else None
    if progress:
        print(f"{YELLOW}Resuming from step: {progress.step}{RESET}\n")
        start_step = progress.step

    steps = ['fetch', 'parse_happy_hours', 'overrides', 'parse_menus', 'summary']

    try:
        start_idx = steps.index(start_step)
        steps_to_run = steps[start_idx:]
        print(f"Running steps: {', '.join(steps_to_run)}\n")

        restaurants = []

        if 'fetch' in steps_to_run:
            restaurants = await async_step_fetch_restaurants(storage)
            save_progress(ProcessingState('parse_happy_hours'))
        else:
            restaurants = storage.read('happy_hours.csv', Restaurant)
            print(f"Loaded {len(restaurants)} restaurants from CSV")

        if 'parse_happy_hours' in steps_to_run:
            restaurants = await async_step_parse_happy_hours(restaurants, storage)
            save_progress(ProcessingState('overrides'))

        if 'overrides' in steps_to_run:
            restaurants = step_apply_overrides(restaurants, storage)
            save_progress(ProcessingState('parse_menus'))

        if 'parse_menus' in steps_to_run:
            restaurants = await async_step_parse_menus(restaurants, storage)
            save_progress(ProcessingState('summary'))

        if 'summary' in steps_to_run:
            step_generate_summary(restaurants)

        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()

        print(f"\n{GREEN}Pipeline complete!{RESET}")

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Interrupted. Progress saved. Resume with --resume{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Happy Hour Data Pipeline Orchestrator'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full pipeline from start'
    )
    parser.add_argument(
        '--step',
        choices=['fetch', 'overrides', 'parse_happy_hours', 'parse_menus', 'summary'],
        help='Start from specific step'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last saved progress'
    )

    args = parser.parse_args()

    if args.full or (not args.step and not args.resume):
        asyncio.run(run_pipeline_async(start_step='fetch'))
    elif args.resume:
        asyncio.run(run_pipeline_async(resume=True))
    elif args.step:
        asyncio.run(run_pipeline_async(start_step=args.step))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
