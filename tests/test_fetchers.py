"""
Tests for fetchers module.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from scripts.fetchers.website import (
    WebsiteFetcher,
    extract_menu_images,
    extract_happy_hour_links,
    normalize_url,
)


def test_normalize_url_adds_http():
    """Test URL normalization adds http://."""
    assert normalize_url("example.com") == "http://example.com"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_returns_none_for_empty():
    """Test empty URL returns None."""
    assert normalize_url("") is None
    assert normalize_url(None) is None


def test_website_fetcher_clean_html():
    """Test HTML cleaning removes tags and scripts."""
    fetcher = WebsiteFetcher()
    
    html = """
    <html>
    <head><script>alert('xss')</script></head>
    <body>
        <h1>Title</h1>
        <p>Paragraph with <b>bold</b> text.</p>
        <style>.css{}</style>
    </body>
    </html>
    """
    
    cleaned = fetcher.clean_html(html)
    
    assert '<script>' not in cleaned
    assert '<style>' not in cleaned
    assert '<h1>' not in cleaned
    assert 'Title' in cleaned
    assert 'Paragraph with bold text' in cleaned


def test_website_fetcher_truncates_long_content():
    """Test cleaning truncates to 8000 chars."""
    fetcher = WebsiteFetcher()
    
    html = '<p>' + 'x' * 10000 + '</p>'
    cleaned = fetcher.clean_html(html)
    
    assert len(cleaned) <= 8000


@patch('scripts.fetchers.website.requests.head')
def test_find_menu_page_checks_priority_paths(mock_head):
    """Test find_menu_page checks priority paths."""
    # First path returns 200, others fail
    mock_head.side_effect = [
        Mock(status_code=200),  # /menus/happy-hour succeeds
    ]
    
    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("http://example.com")
    
    assert result == "http://example.com/menus/happy-hour"
    mock_head.assert_called_once()


@patch('scripts.fetchers.website.requests.head')
def test_find_menu_page_falls_through_to_happy_hour(mock_head):
    """Test find_menu_page falls through to /happy-hour when /menus/happy-hour is 404."""
    import requests as _requests
    mock_head.side_effect = [
        Mock(status_code=404),  # /menus/happy-hour fails
        Mock(status_code=404),  # /menu/happy-hour fails
        Mock(status_code=200),  # /happy-hour succeeds
    ]

    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("http://example.com")

    assert result == "http://example.com/happy-hour"
    assert mock_head.call_count == 3


# ---------------------------------------------------------------------------
# extract_happy_hour_links
# ---------------------------------------------------------------------------

def test_extract_happy_hour_links_href_keyword():
    """Links with happy-hour in href are returned."""
    html = '<a href="/menus/happy-hour">Happy Hour</a>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert "https://example.com/menus/happy-hour" in links


def test_extract_happy_hour_links_anchor_text():
    """Links with happy-hour keyword in anchor text are returned."""
    html = '<a href="/drinks">Happy Hour Specials</a>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert "https://example.com/drinks" in links


def test_extract_happy_hour_links_data_href_button():
    """JS-driven button links are returned when their text is relevant."""
    html = '<button data-href="/weekly-specials">Weekly Specials</button>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert "https://example.com/weekly-specials" in links


def test_extract_happy_hour_links_allows_www_same_site():
    """Bare and www host variants are treated as the same restaurant site."""
    html = '<a href="https://www.example.com/happy-hour">Happy Hour</a>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert links == ["https://www.example.com/happy-hour"]


def test_extract_happy_hour_links_specials_text():
    """Links with 'specials' keyword in anchor text are returned."""
    html = '<a href="/weekly">Weekly Specials</a>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert "https://example.com/weekly" in links


def test_extract_happy_hour_links_ignores_external():
    """Links to other domains are ignored."""
    html = '<a href="https://other.com/happy-hour">Happy Hour</a>'
    links = extract_happy_hour_links(html, "https://example.com")
    assert links == []


def test_extract_happy_hour_links_deduplicates():
    """Duplicate hrefs are returned only once."""
    html = (
        '<a href="/happy-hour">Happy Hour</a>'
        '<a href="/happy-hour">Happy Hour Again</a>'
    )
    links = extract_happy_hour_links(html, "https://example.com")
    assert links.count("https://example.com/happy-hour") == 1


def test_extract_happy_hour_links_max_five():
    """At most 5 links are returned."""
    hrefs = [f'/specials-{i}' for i in range(10)]
    html = ''.join(f'<a href="{h}">Specials</a>' for h in hrefs)
    links = extract_happy_hour_links(html, "https://example.com")
    assert len(links) <= 5


def test_extract_happy_hour_links_empty_html():
    """Empty HTML returns empty list."""
    assert extract_happy_hour_links('', 'https://example.com') == []


# ---------------------------------------------------------------------------
# extract_menu_images
# ---------------------------------------------------------------------------


def test_extract_menu_images_finds_srcset_and_lazy_attrs():
    html = (
        '<picture><source srcset="/img/happy-hour-small.webp 400w, '
        '/img/happy-hour-large.webp 1000w"></picture>'
        '<img data-src="/img/menu.jpg" alt="Food menu">'
    )
    images = extract_menu_images(html, "https://example.com/happy-hour")
    assert images == [
        "https://example.com/img/happy-hour-small.webp",
        "https://example.com/img/happy-hour-large.webp",
        "https://example.com/img/menu.jpg",
    ]


def test_extract_menu_images_finds_contextual_background_image():
    html = '<div class="happy-hour" style="background-image:url(/specials.png)">Deals</div>'
    images = extract_menu_images(html, "https://example.com")
    assert images == ["https://example.com/specials.png"]


def test_extract_menu_images_ignores_unrelated_logo():
    html = '<img src="/logo.png" alt="Company logo"><img src="/patio.jpg" alt="Patio">'
    images = extract_menu_images(html, "https://example.com")
    assert images == []


# ---------------------------------------------------------------------------
# find_menu_page crawl fallback (sync)
# ---------------------------------------------------------------------------

@patch('scripts.fetchers.website.requests.head')
@patch('scripts.fetchers.website.requests.get')
def test_find_menu_page_crawl_fallback(mock_get, mock_head):
    """When all priority paths 404, crawl homepage links."""
    from scripts.fetchers.website import GENERIC_PRIORITY_PATHS, PRIORITY_PATHS
    explicit_count = len([p for p in PRIORITY_PATHS if p not in GENERIC_PRIORITY_PATHS])
    # All priority HEAD checks return 404.
    mock_head.side_effect = (
        [Mock(status_code=404)] * explicit_count
        + [Mock(status_code=200)]  # crawled link succeeds
    )
    mock_get.return_value = Mock(
        text='<a href="/weekly-specials">Weekly Specials</a>',
        status_code=200,
    )

    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("https://example.com")

    assert result == "https://example.com/weekly-specials"


@patch('scripts.fetchers.website.requests.head')
@patch('scripts.fetchers.website.requests.get')
def test_find_menu_page_crawl_beats_generic_menu(mock_get, mock_head):
    """Site-authored specials links win over broad /menu paths."""
    from scripts.fetchers.website import PRIORITY_PATHS, GENERIC_PRIORITY_PATHS
    explicit_count = len([p for p in PRIORITY_PATHS if p not in GENERIC_PRIORITY_PATHS])

    mock_head.side_effect = (
        [Mock(status_code=404)] * explicit_count
        + [Mock(status_code=200)]  # crawled /weekly-specials
    )
    mock_get.return_value = Mock(
        text='<a href="/weekly-specials">Weekly Specials</a>',
        status_code=200,
    )

    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("https://example.com")

    assert result == "https://example.com/weekly-specials"


@patch('scripts.fetchers.website.requests.head')
def test_find_menu_page_strips_query_before_priority_paths(mock_head):
    """Priority path probing appends after the path, not tracking query params."""
    mock_head.return_value = Mock(status_code=200)

    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("https://example.com/location?utm_source=gmb")

    assert result == "https://example.com/location/menus/happy-hour"
    called_url = mock_head.call_args[0][0]
    assert called_url == "https://example.com/location/menus/happy-hour"


@patch('scripts.fetchers.website.requests.head')
@patch('scripts.fetchers.website.requests.get')
def test_find_menu_page_fallback_to_base_when_crawl_empty(mock_get, mock_head):
    """Falls back to base URL when homepage has no relevant links."""
    from scripts.fetchers.website import PRIORITY_PATHS
    mock_head.side_effect = [Mock(status_code=404)] * len(PRIORITY_PATHS)
    mock_get.return_value = Mock(text='<a href="/contact">Contact</a>', status_code=200)

    fetcher = WebsiteFetcher()
    result = fetcher.find_menu_page("https://example.com")

    assert result == "https://example.com"


# ---------------------------------------------------------------------------
# afind_menu_page crawl fallback (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_afind_menu_page_crawl_fallback():
    """Async: when all priority paths 404, crawl homepage links."""
    from scripts.fetchers.website import AsyncWebsiteFetcher

    homepage_html = '<a href="/weekly-specials">Happy Hour Deals</a>'

    async def fake_head(url, timeout=10):
        # Priority paths all 404; crawled URL returns 200.
        if url.endswith('/weekly-specials') and 'example.com' in url:
            return Mock(status_code=200)
        return Mock(status_code=404)

    async def fake_fetch(url, use_cache=True):
        return homepage_html

    fetcher = AsyncWebsiteFetcher(enable_js_render=False)
    fetcher.client.head = fake_head  # type: ignore[assignment]
    fetcher.afetch = fake_fetch  # type: ignore[assignment]

    result = await fetcher.afind_menu_page("https://example.com")
    assert result == "https://example.com/weekly-specials"
    await fetcher.close()
