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
from fetchers import WebsiteFetcher
from fetchers.google_places import fetch_92116_restaurants
from fetchers.google_places_async import AsyncGooglePlacesFetcher
from fetchers.grid import generate_grid, GridCell, get_all_preset_names
from fetchers.google_cache import GoogleAPICache
from processors import HappyHourProcessor, MenuProcessor

try:
    from ai.openrouter import AsyncOpenRouterClient
except ImportError:
    AsyncOpenRouterClient = None  # httpx not available

try:
    from fetchers.website import AsyncWebsiteFetcher
except ImportError:
    AsyncWebsiteFetcher = None  # httpx not available

try:
    from processors.happy_hours_async import AsyncHappyHourProcessor
except ImportError:
    AsyncHappyHourProcessor = None  # httpx not available

try:
    from processors.menus_async import AsyncMenuProcessor
except ImportError:
    AsyncMenuProcessor = None  # httpx not available


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

def _get_fresh_place_ids(existing_restaurants: list, stale_days: int) -> set:
    """Return place_ids that are fresh enough to skip re-fetching."""
    if stale_days <= 0:
        return set()
    cutoff = datetime.now().timestamp() - (stale_days * 86400)
    fresh_ids = set()
    for r in existing_restaurants:
        pid = getattr(r, 'place_id', '') or ''
        if not pid:
            continue
        fd = getattr(r, 'freshness_date', '') or ''
        if not fd:
            continue
        try:
            # freshness_date is ISO date string like "2024-01-15"
            ts = datetime.strptime(fd, "%Y-%m-%d").timestamp()
            if ts >= cutoff:
                fresh_ids.add(pid)
        except ValueError:
            continue
    return fresh_ids


async def async_step_fetch_restaurants(
    storage: CSVManager,
    grid_cells: list = None,
    stale_days: int = 0,
    invalidate_cache: bool = False,
) -> list:
    """Fetch restaurants using async Google Places API."""
    print_step("Fetch Restaurants from Google Places (Async)")
    csv_path = DATA_DIR / 'happy_hours.csv'
    existing_restaurants = []
    if csv_path.exists():
        print(f"Found existing {csv_path}")
        existing_restaurants = storage.read('happy_hours.csv', Restaurant)

    if AsyncGooglePlacesFetcher is None:
        raise RuntimeError("httpx is required for async fetching. Install: pip install httpx")

    # Setup cache
    google_cache = GoogleAPICache(CACHE_DIR / 'google_api')
    if invalidate_cache:
        print("Invalidating Google API cache...")
        google_cache.invalidate_all()

    # Determine which places are fresh enough to skip
    skip_place_ids = _get_fresh_place_ids(existing_restaurants, stale_days)
    if skip_place_ids:
        print(f"Skipping {len(skip_place_ids)} fresh places (stale_days={stale_days})")

    print("Fetching from Google Places API...")
    try:
        async with AsyncGooglePlacesFetcher(
            api_key=os.environ.get("GOOGLE_PLACES_API_KEY", ""),
            details_concurrency=GOOGLE_PLACES_CONCURRENCY,
            cache=google_cache,
        ) as fetcher:
            restaurants = await fetcher.fetch_restaurants(
                grid_cells=grid_cells,
                skip_place_ids=skip_place_ids,
            )

        for r in restaurants:
            r.freshness_date = datetime.now().isoformat()[:10]

        # Merge fresh (skipped) restaurants back in
        if skip_place_ids and existing_restaurants:
            skipped = [r for r in existing_restaurants if (getattr(r, 'place_id', '') or '') in skip_place_ids]
            print(f"Restoring {len(skipped)} skipped fresh restaurants to results...")
            # Build lookup by place_id for dedup
            by_id = {r.place_id: r for r in restaurants if getattr(r, 'place_id', '')}
            for s in skipped:
                if s.place_id not in by_id:
                    restaurants.append(s)
                    by_id[s.place_id] = s

        # Merge into existing CSV instead of overwriting
        if csv_path.exists() and restaurants:
            print(f"\nMerging {len(restaurants)} fetched restaurants into existing CSV...")
            restaurants = storage.merge_by_place_id('happy_hours.csv', restaurants, Restaurant)
        else:
            storage.write('happy_hours.csv', restaurants)
            print(f"Saved {len(restaurants)} restaurants to happy_hours.csv")
        return restaurants
    except Exception as e:
        print(f"{RED}Error fetching from API: {e}{RESET}")
        print("Falling back to CSV...")
        restaurants = storage.read('happy_hours.csv', Restaurant)
        print(f"Loaded {len(restaurants)} restaurants from CSV")
        return restaurants


async def async_step_parse_happy_hours(restaurants: list, storage: CSVManager) -> list:
    """Parse happy hours concurrently using AI."""
    if AsyncOpenRouterClient is None or AsyncWebsiteFetcher is None or AsyncHappyHourProcessor is None:
        raise RuntimeError("httpx is required for async AI parsing. Install: pip install httpx")

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
    if AsyncOpenRouterClient is None or AsyncWebsiteFetcher is None or AsyncMenuProcessor is None:
        raise RuntimeError("httpx is required for async AI parsing. Install: pip install httpx")

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

async def run_pipeline_async(
    start_step: str = 'load',
    resume: bool = False,
    grid_cells: list = None,
    fetch_only: bool = False,
    stale_days: int = 0,
    invalidate_cache: bool = False,
):
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
        if fetch_only:
            steps_to_run = ['fetch']
        print(f"Running steps: {', '.join(steps_to_run)}\n")

        restaurants = []

        if 'fetch' in steps_to_run:
            restaurants = await async_step_fetch_restaurants(
                storage,
                grid_cells=grid_cells,
                stale_days=stale_days,
                invalidate_cache=invalidate_cache,
            )
            if fetch_only:
                print(f"\n{GREEN}Fetch-only complete. {len(restaurants)} restaurants in CSV.{RESET}")
                return restaurants
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
        help='Run full pipeline from start (full adaptive grid)'
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
    parser.add_argument(
        '--area',
        choices=get_all_preset_names(),
        help='Run on a specific neighborhood preset (fast debug)'
    )
    parser.add_argument(
        '--cell',
        help='Run on a single grid cell as lat,lng (e.g. 32.762,-117.119)'
    )
    parser.add_argument(
        '--bbox',
        help='Custom bounding box as south,west,north,east (e.g. 32.64,-117.28,32.88,-117.08)'
    )
    parser.add_argument(
        '--fetch-only',
        action='store_true',
        help='Only fetch from Google Places, skip AI parsing (fast debug)'
    )
    parser.add_argument(
        '--stale-days',
        type=int,
        default=30,
        help='Skip re-fetching Place Details for restaurants fresher than N days (default: 30)'
    )
    parser.add_argument(
        '--invalidate-cache',
        action='store_true',
        help='Clear Google API cache before fetching'
    )

    args = parser.parse_args()

    # Build grid_cells from CLI flags
    grid_cells = None
    if args.area:
        grid_cells = generate_grid(preset=args.area)
        print(f"Using neighborhood preset: {args.area}")
    elif args.cell:
        try:
            lat, lng = args.cell.split(',')
            # Create a small ~1.5x1.5 mile cell around the point
            lat_f = float(lat)
            lng_f = float(lng)
            cell = GridCell(
                south=lat_f - 0.012,
                west=lng_f - 0.015,
                north=lat_f + 0.012,
                east=lng_f + 0.015,
            )
            grid_cells = [cell]
            print(f"Using single cell around {lat_f},{lng_f}")
        except ValueError:
            print(f"{RED}Error: --cell must be lat,lng{RESET}")
            sys.exit(1)
    elif args.bbox:
        try:
            parts = args.bbox.split(',')
            if len(parts) != 4:
                raise ValueError()
            bbox = {
                "south": float(parts[0]),
                "west": float(parts[1]),
                "north": float(parts[2]),
                "east": float(parts[3]),
            }
            grid_cells = generate_grid(bbox=bbox)
            print(f"Using custom bounding box")
        except ValueError:
            print(f"{RED}Error: --bbox must be south,west,north,east{RESET}")
            sys.exit(1)
    elif args.full:
        grid_cells = generate_grid()
        print("Using full adaptive grid")

    if args.full or args.area or args.cell or args.bbox:
        asyncio.run(run_pipeline_async(
            start_step='fetch',
            grid_cells=grid_cells,
            fetch_only=args.fetch_only,
            stale_days=args.stale_days,
            invalidate_cache=args.invalidate_cache,
        ))
    elif args.resume:
        asyncio.run(run_pipeline_async(resume=True, stale_days=args.stale_days))
    elif args.step:
        asyncio.run(run_pipeline_async(start_step=args.step, stale_days=args.stale_days))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
