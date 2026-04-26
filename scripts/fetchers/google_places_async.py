"""
Async Google Places API (New) v1 fetcher for high-concurrency restaurant data.
Uses httpx and asyncio.Semaphore to parallelize Place Details calls.
"""
import asyncio
from typing import List, Optional, Dict, Any

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
    ):
        self.api_key = api_key or GOOGLE_PLACES_API_KEY
        self._client = client
        self._owned_client = client is None
        self.details_semaphore = asyncio.Semaphore(details_concurrency)

    @property
    def client(self) -> "httpx.AsyncClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def _search_places_text(
        self,
        location: str,
        radius: int = 2400,
        keyword: str = None,
        page_token: str = None,
    ) -> tuple:
        url = f"{PLACES_API_BASE}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.types,places.primaryType,places.location,nextPageToken"
            ),
        }
        lat, lng = float(location.split(',')[0]), float(location.split(',')[1])
        body = {
            "textQuery": keyword or "restaurant",
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius,
                }
            },
            "maxResultCount": 20,
        }
        if page_token:
            body["pageToken"] = page_token

        response = await self.client.post(url, headers=headers, json=body)
        if response.status_code != 200:
            print(f"Text Search API Error: {response.status_code}")
            return [], None
        data = response.json()
        return data.get('places', []), data.get('nextPageToken')

    async def _search_places_paginated(
        self,
        location: str,
        radius: int = 2400,
        keyword: str = None,
        max_results: int = 60,
    ) -> List[Dict]:
        all_places = []
        page_token = None
        pages = 0
        max_pages = (max_results + 19) // 20

        while len(all_places) < max_results and pages < max_pages:
            places, page_token = await self._search_places_text(
                location, radius, keyword, page_token
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
        url = f"{PLACES_API_BASE}/places/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,types,nationalPhoneNumber,"
                "websiteUri,regularOpeningHours,currentSecondaryOpeningHours,"
                "rating,userRatingCount,priceLevel,location,googleMapsUri,editorialSummary"
            ),
        }
        async with self.details_semaphore:
            response = await self.client.get(url, headers=headers)
        if response.status_code != 200:
            print(f"    API Error: {response.status_code}")
            return None
        return response.json()

    async def fetch_all_places(
        self,
        location: str,
        radius: int = 800,
        keywords: List[str] = None,
    ) -> List[Dict]:
        center_lat, center_lng = float(location.split(',')[0]), float(location.split(',')[1])
        all_places: Dict[str, Dict] = {}

        if keywords is None:
            keywords = ["restaurant", "bar", "happy hour", "pub", "grill", "kitchen", "brewery"]

        print("=" * 60)
        print("FETCHING ALL PLACES (async text search with pagination)")
        print("=" * 60)

        for keyword in keywords:
            print(f"\n[Searching] '{keyword}'")
            places = await self._search_places_paginated(
                location, radius, keyword=keyword, max_results=60
            )
            for place in places:
                pid = place.get('id')
                if pid and pid not in all_places:
                    all_places[pid] = place
            print(f"  Found {len(places)} places (total unique: {len(all_places)})")

        print(f"\nFiltering by distance ({radius}m radius)...")
        places_list = list(all_places.values())
        filtered = filter_by_distance(places_list, center_lat, center_lng, radius)
        print(f"  Kept {len(filtered)}/{len(places_list)} places within {radius}m")

        print(f"\n{'=' * 60}")
        print(f"TOTAL PLACES WITHIN {radius}m: {len(filtered)}")
        print(f"{'=' * 60}")

        return filtered

    async def fetch_restaurants(
        self,
        location: str = "32.762889,-117.119922",
        radius: int = 4000,
        max_results: int = 200,
    ) -> List[Restaurant]:
        print(f"Fetching restaurants near {location}")
        print(f"Radius: {radius}m (~2.5 miles), Target: {max_results} places\n")

        all_places = await self.fetch_all_places(location, radius=radius)

        if len(all_places) > max_results:
            print(f"\nLimiting to {max_results} places (found {len(all_places)})")
            all_places = all_places[:max_results]

        print(f"\nProcessing {len(all_places)} places for details...")

        # Fetch all details concurrently
        async def process_one(place_summary: Dict, idx: int) -> Optional[Restaurant]:
            place_id = place_summary.get('id')
            name = place_summary.get('displayName', {}).get('text', 'Unknown')
            try:
                print(f"[{idx}/{len(all_places)}] {name}...")
            except UnicodeEncodeError:
                print(f"[{idx}/{len(all_places)}] <Unicode name>...")

            details = await self._get_place_details(place_id)
            if not details:
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
        hh_count = sum(1 for r in restaurants if r.happy_hour_times)

        print(f"\n{'='*60}")
        print(f"Total: {len(restaurants)} restaurants")
        print(f"With happy hours: {hh_count}")
        print(f"{'='*60}")

        return restaurants

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
