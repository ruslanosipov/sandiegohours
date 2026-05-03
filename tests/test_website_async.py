"""
Tests for AsyncWebsiteFetcher: SPA detection, afetch_clean JS fallback (mocked).
"""
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("httpx")

from scripts.fetchers.website import (
    AsyncWebsiteFetcher,
    JS_RENDER_MIN_CLEANED_CHARS,
)


class TestLooksLikeSpa:
    def test_wix_generator_returns_true(self):
        html = (
            '<!DOCTYPE html><html><head>'
            '<meta name="generator" content="Wix.com Website Builder"/>'
            "</head><body></body></html>"
        )
        assert AsyncWebsiteFetcher._looks_like_spa(html) is True

    def test_squarespace_returns_true(self):
        html = "<html><head><!-- squarespace --></head><body>x</body></html>"
        assert AsyncWebsiteFetcher._looks_like_spa(html) is True

    def test_plain_static_html_returns_false(self):
        html = "<html><body><h1>Welcome</h1><p>Our menu has beer $5</p></body></html>"
        assert AsyncWebsiteFetcher._looks_like_spa(html) is False

    def test_empty_returns_false(self):
        assert AsyncWebsiteFetcher._looks_like_spa("") is False


@pytest.mark.asyncio
class TestAfetchClean:
    async def test_long_static_html_skips_render(self):
        """Enough cleaned text + no SPA marker => no _render_js call."""
        fetcher = AsyncWebsiteFetcher(cache_dir=None, enable_js_render=True)
        fetcher._js_enabled = True
        fetcher._render_js = AsyncMock(side_effect=AssertionError("render should not run"))

        body = "<p>" + ("word " * 200) + "</p>"
        fetcher.afetch = AsyncMock(return_value=f"<html><body>{body}</body></html>")

        out = await fetcher.afetch_clean("https://example.com/menu")
        assert out is not None
        assert len(out) >= JS_RENDER_MIN_CLEANED_CHARS
        fetcher._render_js.assert_not_called()
        await fetcher.close()

    async def test_short_html_calls_render_and_prefers_longer_result(self):
        fetcher = AsyncWebsiteFetcher(cache_dir=None, enable_js_render=True)
        fetcher._js_enabled = True
        rendered = "menu item beer draft $5 " * 40
        fetcher._render_js = AsyncMock(return_value=rendered)
        fetcher.afetch = AsyncMock(return_value="<html><body><p>x</p></body></html>")

        out = await fetcher.afetch_clean("https://example.com/x")
        assert out == rendered
        fetcher._render_js.assert_called_once()
        await fetcher.close()

    async def test_spa_marker_triggers_render_even_when_cleaned_short(self):
        fetcher = AsyncWebsiteFetcher(cache_dir=None, enable_js_render=True)
        fetcher._js_enabled = True
        rendered = "wine glass $8 " * 50
        fetcher._render_js = AsyncMock(return_value=rendered)
        wix = (
            '<html><head><meta name="generator" content="Wix.com Website Builder"/>'
            "</head><body></body></html>"
        )
        fetcher.afetch = AsyncMock(return_value=wix)

        out = await fetcher.afetch_clean("https://wix.example.com/")
        assert out == rendered
        fetcher._render_js.assert_called_once()
        await fetcher.close()

    async def test_keeps_static_when_render_not_longer(self):
        """SPA path runs render, but if render is shorter than cleaned text, keep static."""
        fetcher = AsyncWebsiteFetcher(cache_dir=None, enable_js_render=True)
        fetcher._js_enabled = True
        fetcher._render_js = AsyncMock(return_value="tiny")
        # Wix marker forces needs_render; body still yields ~50 chars cleaned after strip
        wix_shell = (
            '<html><head><meta name="generator" content="Wix.com Website Builder"/></head>'
            "<body><p>" + ("visible " * 8) + "</p></body></html>"
        )
        fetcher.afetch = AsyncMock(return_value=wix_shell)

        out = await fetcher.afetch_clean("https://wix.example.com/x")
        cleaned = fetcher.clean_html(wix_shell)
        assert len(cleaned) > len("tiny")
        assert out == cleaned
        fetcher._render_js.assert_called_once()
        await fetcher.close()

    async def test_render_cache_short_circuits_before_fetch(self):
        tmp = tempfile.mkdtemp()
        cache_dir = Path(tmp)
        url = "https://example.com/cached"
        fetcher = AsyncWebsiteFetcher(cache_dir=cache_dir, enable_js_render=True)
        fetcher._js_enabled = True
        key = fetcher._cache_key(url)
        cached_text = "cached line " * 50
        (cache_dir / f"{key}.rendered.txt").write_text(cached_text, encoding="utf-8")

        fetcher.afetch = AsyncMock(side_effect=AssertionError("afetch should not run"))
        fetcher._render_js = AsyncMock(side_effect=AssertionError("render should not run"))

        out = await fetcher.afetch_clean(url)
        assert out == cached_text
        await fetcher.close()
