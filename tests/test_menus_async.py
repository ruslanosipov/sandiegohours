"""
Tests for AsyncMenuProcessor homepage fallback when priority-path URL is too short.
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from processors.menus_async import AsyncMenuProcessor
from storage import Restaurant


class FakeFetcherShortThenHome:
    """First URL (e.g. /happyhour) returns too little text; /home returns enough."""

    def __init__(self):
        self.afetch_clean_urls: list[str] = []

    async def afind_menu_page(self, base_url: str) -> str:
        return "https://example.com/happyhour"

    async def afetch_clean(self, url: str) -> str:
        self.afetch_clean_urls.append(url)
        if "happyhour" in url:
            return "x" * 50
        if url.rstrip("/").endswith("example.com/home") or url.endswith("/home"):
            return "beer draft $5 " * 50
        if url == "https://example.com/":
            return "z" * 100
        return ""


class FakeFetcherAdequateFirst:
    """Priority path already returns enough text — no /home retry needed."""

    def __init__(self):
        self.afetch_clean_urls: list[str] = []

    async def afind_menu_page(self, base_url: str) -> str:
        return "https://example.com/happyhour"

    async def afetch_clean(self, url: str) -> str:
        self.afetch_clean_urls.append(url)
        return "wing plate $3 beer draft $5 " * 40


class MockOpenRouter:
    def __init__(self, response_json: str):
        self._response = response_json
        self.acomplete_calls: list[tuple] = []

    async def acomplete(self, prompt: str, system: str = None, temperature: float = 0.1):
        self.acomplete_calls.append((prompt, system))
        return self._response


@pytest.mark.asyncio
async def test_menu_processor_retries_home_when_first_url_too_short():
    menu_json = (
        '{"drink": {"name": "$5 beer draft", "price": 5.0}, '
        '"food": null, "short_summary": "beer draft $5"}'
    )
    ai = MockOpenRouter(menu_json)
    fetcher = FakeFetcherShortThenHome()
    processor = AsyncMenuProcessor(ai, fetcher)

    r = Restaurant(
        restaurant_name="Example Bar",
        address="123 St",
        website_url="https://example.com",
    )

    ok = await processor.process(r)
    assert ok is True
    assert r.cheapest_drink == "$5 beer draft"
    assert r.cheapest_drink_price == 5.0
    # Fetched short page first, then /home
    assert "https://example.com/happyhour" in fetcher.afetch_clean_urls
    assert any("/home" in u for u in fetcher.afetch_clean_urls)
    # AI should receive the long /home text (contains beer draft)
    prompt_text = ai.acomplete_calls[0][0]
    assert "beer draft" in prompt_text.lower()


@pytest.mark.asyncio
async def test_menu_processor_skips_home_when_first_fetch_usable():
    menu_json = (
        '{"drink": {"name": "$5 beer draft", "price": 5.0}, '
        '"food": null, "short_summary": "beer draft $5"}'
    )
    ai = MockOpenRouter(menu_json)
    fetcher = FakeFetcherAdequateFirst()
    processor = AsyncMenuProcessor(ai, fetcher)

    r = Restaurant(
        restaurant_name="Example Bar 2",
        address="456 St",
        website_url="https://example.com",
    )

    ok = await processor.process(r)
    assert ok is True
    assert len(fetcher.afetch_clean_urls) == 1
    assert fetcher.afetch_clean_urls[0] == "https://example.com/happyhour"
