"""
Tests for AsyncHappyHourProcessor crawl fallbacks.
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from processors.happy_hours_async import AsyncHappyHourProcessor
from storage import Restaurant


class MockOpenRouter:
    def __init__(self, response_json: str):
        self._response = response_json
        self.acomplete_calls: list[tuple] = []

    async def acomplete(self, prompt: str, system: str = None, temperature: float = 0.1):
        self.acomplete_calls.append((prompt, system))
        return self._response


class FakeFetcherShortThenHome:
    def __init__(self):
        self.afetch_clean_urls: list[str] = []

    async def afind_menu_page(self, base_url: str) -> str:
        return "https://example.com/happyhour"

    async def afetch_clean(self, url: str) -> str:
        self.afetch_clean_urls.append(url)
        if url == "https://example.com/happyhour":
            return "x" * 50
        if url == "https://example.com/home":
            return "Happy Hour Monday-Friday 3 PM - 6 PM draft beer and appetizers " * 10
        return ""

    async def afetch_menu_images(self, url: str) -> list[str]:
        return []


class FakeFetcherImageOnly:
    async def afind_menu_page(self, base_url: str) -> str:
        return "https://example.com/happy-hour"

    async def afetch_clean(self, url: str) -> str:
        return ""

    async def afetch_menu_images(self, url: str) -> list[str]:
        return ["https://example.com/happy-hour.png"]


class MockVisionOpenRouter(MockOpenRouter):
    def __init__(self, text_response: str, vision_response: str):
        super().__init__(text_response)
        self._vision_response = vision_response
        self.image_calls: list[tuple] = []

    async def acomplete_with_images(
        self,
        prompt: str,
        image_urls: list,
        system: str = None,
        temperature: float = 0.1,
        vision_model: str = None,
    ):
        self.image_calls.append((prompt, image_urls, system))
        return self._vision_response


@pytest.mark.asyncio
async def test_happy_hour_processor_retries_home_when_first_url_too_short():
    ai = MockOpenRouter(
        '{"happy_hours": [{"day": "Monday", "times": "3:00 PM - 6:00 PM"}], '
        '"confidence": "high"}'
    )
    fetcher = FakeFetcherShortThenHome()
    processor = AsyncHappyHourProcessor(ai, fetcher)

    r = Restaurant(
        restaurant_name="Example Bar",
        address="123 St",
        website_url="https://example.com?utm_source=google",
    )

    ok = await processor.process(r)

    assert ok is True
    assert r.happy_hour_times == "Monday: 3:00 PM - 6:00 PM"
    assert "https://example.com/happyhour" in fetcher.afetch_clean_urls
    assert "https://example.com/home" in fetcher.afetch_clean_urls
    assert "Happy Hour Monday-Friday" in ai.acomplete_calls[0][0]


@pytest.mark.asyncio
async def test_happy_hour_processor_uses_vision_for_image_only_schedule():
    ai = MockVisionOpenRouter(
        text_response='{"happy_hours": [], "confidence": "none"}',
        vision_response=(
            '{"happy_hours": [{"day": "Tuesday", "times": "4:00 PM - 7:00 PM"}], '
            '"confidence": "high"}'
        ),
    )
    processor = AsyncHappyHourProcessor(ai, FakeFetcherImageOnly())

    r = Restaurant(
        restaurant_name="Image Bar",
        address="456 St",
        website_url="https://example.com",
    )

    ok = await processor.process(r)

    assert ok is True
    assert r.happy_hour_times == "Tuesday: 4:00 PM - 7:00 PM"
    assert r.source == "Website image (AI parsed, high confidence)"
    assert ai.image_calls[0][1] == ["https://example.com/happy-hour.png"]
