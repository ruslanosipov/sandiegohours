"""
Tests for fetchers module.
"""
import pytest
from unittest.mock import Mock, patch
from scripts.fetchers.website import WebsiteFetcher, normalize_url


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
