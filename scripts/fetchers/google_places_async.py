"""
Async Google Places API (New) v1 fetcher for high-concurrency restaurant data.
Uses httpx and asyncio.Semaphore to parallelize Place Details calls.

COST OPTIMIZATIONS:
- Text Search uses IDs Only field mask (free tier, unlimited)
- Place Details uses Pro tier (no editorialSummary)
- Disk cache for Place Details to avoid repeat API calls
"""
import asyncio
from typing import List, Optional, Dict, Any, Set

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage import Restaurant

# Re-use sync helpers that have no I/O
from fetchers.google_places import (
    parse_secondary_opening_hours,
    convert_to_restaurant,
    filter_by_distance,
    calculate_distance_meters,
)
from fetchers.grid import (
    GridCell,
    subdivide_cell,
    should_subdivide,
    get_keywords_for_cell,
    should_exclude_place,
    TIER1_KEYWORDS,
)

try:
    from fetchers.google_cache import GoogleAPICache
except ImportError:
    GoogleAPICache = None

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
PLACES_API_BASE = "https://places.googleapis.com/v1"

# Concurrency caps
PLACE_DETAILS_CONCURRENCY = 10
TEXT_SEARCH_DELAY = 0.5


class AsyncGooglePlacesFetcher:
    """High-performance async fetcher for Google Places API (New) v1."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional["httpx.AsyncClient"] = None,
        details_concurrency: int = PLACE_DETAILS_CONCURRENCY,
        cache: Optional["GoogleAPICache"] = None,
    ):
        self.api_key = api_key or GOOGLE_PLACES_API_KEY
        self._client = client
        self._owned_client = client is None
        self.details_semaphore = asyncio.Semaphore(details_concurrency)
        self.cache = cache

    @property
    def client(self) -> "httpx.AsyncClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def _search_places_text(
        self,
        location: str = None,
        radius: int = 2400,
        keyword: str = None,
        page_token: str = None,
        location_restriction: dict = None,
    ) -> tuple:
        # Check cache first
        if self.cache:
            cached = self.cache.get_search(
                keyword=keyword or "restaurant",
                location=location,
                radius=radius,
                page_token=page_token,
                location_restriction=location_restriction,
            )
            if cached is not None:
                return cached.get("places", []), cached.get("nextPageToken")

        url = f"{PLACES_API_BASE}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,nextPageToken",
        }
        body = {
            "textQuery": keyword or "restaurant",
            "maxResultCount": 20,
        }
        if location_restriction:
            body["locationRestriction"] = location_restriction
        elif location:
            lat, lng = float(location.split(',')[0]), float(location.split(',')[1])
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius,
                }
            }
        if page_token:
            body["pageToken"] = page_token

        response = await self.client.post(url, headers=headers, json=body)
        if response.status_code != 200:
            print(f"Text Search API Error: {response.status_code}")
            return [], None
        data = response.json()

        # Cache result
        if self.cache:
            self.cache.set_search(
                keyword=keyword or "restaurant",
                location=location,
                radius=radius,
                page_token=page_token,
                location_restriction=location_restriction,
                result=data,
            )

        return data.get('places', []), data.get('nextPageToken')

    async def _search_places_paginated(
        self,
        location: str = None,
        radius: int = 2400,
        keyword: str = None,
        max_results: int = 60,
        location_restriction: dict = None,
    ) -> List[Dict]:
        all_places = []
        page_token = None
        pages = 0
        max_pages = (max_results + 19) // 20

        while len(all_places) < max_results and pages < max_pages:
            places, page_token = await self._search_places_text(
                location=location,
                radius=radius,
                keyword=keyword,
                page_token=page_token,
                location_restriction=location_restriction,
            )
            if not places:
                break
            all_places.extend(places)
            pages += 1
            if not page_token:
                break
            await asyncio.sleep(TEXT_SEARCH_DELAY)

        return all_places[:max_results]

    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        # Check cache first
        if self.cache:
            cached = self.cache.get_details(place_id)
            if cached is not None:
                return cached

        url = f"{PLACES_API_BASE}/places/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,types,nationalPhoneNumber,"
                "websiteUri,regularOpeningHours,currentSecondaryOpeningHours,"
                "rating,userRatingCount,priceLevel,location,googleMapsUri"
            ),
        }
        async with self.details_semaphore:
            response = await self.client.get(url, headers=headers)
        if response.status_code != 200:
            print(f"    API Error: {response.status_code}")
            return None
        data = response.json()

        # Cache result
        if self.cache:
            self.cache.set_details(place_id, data)

        return data

    async def fetch_all_places(
        self,
        location: str = None,
        radius: int = 800,
        keywords: List[str] = None,
        location_restriction: dict = None,
    ) -> List[Dict]:
        all_places: Dict[str, Dict] = {}

        if keywords is None:
            keywords = ["restaurant", "bar", "happy hour", "pub", "grill", "kitchen", "brewery"]

        print("=" * 60)
        print("FETCHING ALL PLACES (async text search with pagination)")
        print("=" * 60)

        for keyword in keywords:
            print(f"\n[Searching] '{keyword}'")
            places = await self._search_places_paginated(
                location=location,
                radius=radius,
                keyword=keyword,
                max_results=60,
                location_restriction=location_restriction,
            )
            for place in places:
                pid = place.get('id')
                if pid and pid not in all_places:
                    all_places[pid] = place
            print(f"  Found {len(places)} places (total unique: {len(all_places)})")

        print(f"\n{'=' * 60}")
        print(f"TOTAL UNIQUE PLACES: {len(all_places)}")
        print(f"{'=' * 60}")
        return list(all_places.values())

    async def fetch_all_places_for_cell(
        self,
        cell: GridCell,
        keywords: List[str] = None,
    ) -> List[Dict]:
        """
        Fetch all place IDs for a single grid cell using locationRestriction.
        Returns minimal place objects (just id) since text search is IDs Only.
        """
        restriction = cell.to_location_restriction()
        all_places: Dict[str, Dict] = {}

        for keyword in (keywords or TIER1_KEYWORDS):
            places = await self._search_places_paginated(
                location_restriction=restriction,
                keyword=keyword,
                max_results=60,
            )
            for place in places:
                pid = place.get('id')
                if pid and pid not in all_places:
                    all_places[pid] = place

        return list(all_places.values())

    async def fetch_adaptive_grid(
        self,
        grid_cells: List[GridCell],
    ) -> List[Dict]:
        """
        Fetch places across an adaptive grid.
        Subdivides cells that hit the 60-result cap.
        NOTE: Type filtering now happens AFTER Place Details (ids-only search).
        """
        all_places: Dict[str, Dict] = {}
        cells_to_process = list(grid_cells)

        print(f"\nStarting adaptive grid search with {len(cells_to_process)} initial cell(s)...")

        while cells_to_process:
            cell = cells_to_process.pop(0)
            try:
                print(f"\n  [Cell] {cell.south:.4f},{cell.west:.4f} to {cell.north:.4f},{cell.east:.4f} "
                      f"(~{cell.width_miles():.1f}x{cell.height_miles():.1f} mi)")
            except UnicodeEncodeError:
                print("\n  [Cell] <Unicode cell info>")

            # Use tier1 keywords for truncation detection
            places = await self.fetch_all_places_for_cell(cell, keywords=TIER1_KEYWORDS)
            try:
                print(f"    Tier-1 found {len(places)} unique places")
            except UnicodeEncodeError:
                print("    Tier-1 found <count> unique places")

            if should_subdivide(cell, len(places)):
                children = subdivide_cell(cell)
                cells_to_process.extend(children)
                try:
                    print(f"    -> Subdividing into {len(children)} smaller cells")
                except UnicodeEncodeError:
                    print("    -> Subdividing into smaller cells")
                continue

            # Cell is finalized — also run tier2 keywords to fill gaps
            tier2_keywords = [k for k in get_keywords_for_cell(cell) if k not in TIER1_KEYWORDS]
            if tier2_keywords:
                tier2_places = await self.fetch_all_places_for_cell(cell, keywords=tier2_keywords)
                print(f"    Tier-2 found {len(tier2_places)} unique places")
                for place in tier2_places:
                    pid = place.get('id')
                    if pid and pid not in all_places:
                        all_places[pid] = place

            for place in places:
                pid = place.get('id')
                if pid and pid not in all_places:
                    all_places[pid] = place

        print(f"\n{'='*60}")
        print(f"Grid search complete: {len(all_places)} unique place IDs")
        print(f"{'='*60}")
        return list(all_places.values())

    async def fetch_restaurants(
        self,
        grid_cells: List[GridCell] = None,
        location: str = "32.762889,-117.119922",
        radius: int = 4000,
        max_results: int = 200,
        skip_place_ids: Optional[Set[str]] = None,
    ) -> List[Restaurant]:
        if grid_cells:
            print(f"Fetching restaurants across {len(grid_cells)} grid cell(s)...\n")
            all_places = await self.fetch_adaptive_grid(grid_cells)
        else:
            print(f"Fetching restaurants near {location}")
            print(f"Radius: {radius}m (~2.5 miles), Target: {max_results} places\n")
            all_places = await self.fetch_all_places(location, radius=radius)

        # Remove skipped (fresh) place IDs
        skip_place_ids = skip_place_ids or set()
        if skip_place_ids:
            before = len(all_places)
            all_places = [p for p in all_places if p.get('id') not in skip_place_ids]
            skipped = before - len(all_places)
            print(f"\nSkipped {skipped} fresh places (stale-days filter)")

        if len(all_places) > max_results:
            print(f"\nLimiting to {max_results} places (found {len(all_places)})")
            all_places = all_places[:max_results]

        print(f"\nProcessing {len(all_places)} places for details...")

        # Fetch all details concurrently
        async def process_one(place_summary: Dict, idx: int) -> Optional[Restaurant]:
            place_id = place_summary.get('id')
            try:
                print(f"[{idx}/{len(all_places)}] {place_id}...")
            except UnicodeEncodeError:
                print(f"[{idx}/{len(all_places)}] <Unicode id>...")

            details = await self._get_place_details(place_id)
            if not details:
                return None

            # Exclude coffee shops, gas stations, etc. before conversion.
            # Preserve places that Google already confirmed have happy hours.
            place_types = details.get('types', []) or []
            sec_hours = details.get('currentSecondaryOpeningHours', []) or []
            has_happy_hours = any(
                e.get('secondaryHoursType', '').upper() == 'HAPPY_HOUR'
                for e in sec_hours
            )
            if should_exclude_place(place_types, has_happy_hours=has_happy_hours):
                return None

            try:
                return convert_to_restaurant(details)
            except Exception as e:
                try:
                    print(f"    Error: {e}")
                except UnicodeEncodeError:
                    print("    Error: <Unicode issue>")
                return None

        tasks = [process_one(p, i + 1) for i, p in enumerate(all_places)]
        results = await asyncio.gather(*tasks)

        restaurants = [r for r in results if r is not None]

        # Apply post-details distance filtering (search is IDs Only, no location data)
        if not grid_cells and location:
            center_lat, center_lng = float(location.split(',')[0]), float(location.split(',')[1])
            print(f"\nFiltering by distance ({radius}m radius)...")
            before = len(restaurants)
            restaurants = self._filter_restaurants_by_distance(restaurants, center_lat, center_lng, radius)
            print(f"  Kept {len(restaurants)}/{before} places within {radius}m")

        hh_count = sum(1 for r in restaurants if r.happy_hour_times)

        print(f"\n{'='*60}")
        print(f"Total: {len(restaurants)} restaurants")
        print(f"With happy hours: {hh_count}")
        print(f"{'='*60}")

        return restaurants

    @staticmethod
    def _filter_restaurants_by_distance(
        restaurants: List[Restaurant], center_lat: float, center_lng: float, max_distance: float
    ) -> List[Restaurant]:
        filtered = []
        for r in restaurants:
            if r.latitude and r.longitude:
                dist = calculate_distance_meters(
                    center_lat, center_lng, float(r.latitude), float(r.longitude)
                )
                if dist <= max_distance:
                    filtered.append(r)
            else:
                # Keep places with missing coordinates (conservative)
                filtered.append(r)
        return filtered

    async def close(self):
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


if not _HAS_HTTPX:
    AsyncGooglePlacesFetcher = None  # type: ignore
