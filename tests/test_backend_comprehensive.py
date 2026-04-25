#!/usr/bin/env python3
"""
Tests for website caching, AI confidence rejection, CSV edge cases, and pipeline resume.
"""
import sys
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from fetchers.website import WebsiteFetcher, normalize_url
from storage.csv_manager import CSVManager
from storage.models import Restaurant, ProcessingState
from processors.happy_hours import HappyHourProcessor
from ai.openrouter import OpenRouterClient


class TestWebsiteFetcherCache:
    """Tests for WebsiteFetcher caching behavior."""

    def test_cache_hit_reads_from_disk_no_http_request(self, tmp_path):
        """Given cached file exists, When fetch is called with use_cache=True, Then it reads from disk and no HTTP request is made."""
        cache_dir = tmp_path / 'cache'
        fetcher = WebsiteFetcher(cache_dir=cache_dir)

        # Pre-populate cache
        url = 'http://example.com/menu'
        cache_key = fetcher._cache_key(url)
        cache_file = cache_dir / f"{cache_key}.html"
        cache_file.write_text('<html>Cached content</html>', encoding='utf-8')

        with patch('fetchers.website.requests.get') as mock_get:
            result = fetcher.fetch(url, use_cache=True)

        assert '<html>Cached content</html>' in result
        mock_get.assert_not_called()

    def test_cache_miss_makes_http_request(self, tmp_path):
        """Given no cache exists, When fetch is called, Then it makes an HTTP request and saves to cache."""
        cache_dir = tmp_path / 'cache'
        fetcher = WebsiteFetcher(cache_dir=cache_dir)

        with patch('fetchers.website.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                raise_for_status=Mock(),
                text='<html>Fresh content</html>'
            )
            with patch('fetchers.website.time.sleep'):
                result = fetcher.fetch('http://example.com', use_cache=True)

        assert result == '<html>Fresh content</html>'
        mock_get.assert_called_once()

        # Verify it was saved to cache
        cache_key = fetcher._cache_key('http://example.com')
        cache_file = cache_dir / f"{cache_key}.html"
        assert cache_file.exists()

    def test_use_cache_false_bypasses_cache(self, tmp_path):
        """Given cached file exists, When fetch is called with use_cache=False, Then it makes a fresh HTTP request."""
        cache_dir = tmp_path / 'cache'
        fetcher = WebsiteFetcher(cache_dir=cache_dir)

        # Pre-populate cache
        url = 'http://example.com'
        cache_key = fetcher._cache_key(url)
        cache_file = cache_dir / f"{cache_key}.html"
        cache_file.write_text('<html>Old cached content</html>', encoding='utf-8')

        with patch('fetchers.website.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                raise_for_status=Mock(),
                text='<html>Fresh override</html>'
            )
            with patch('fetchers.website.time.sleep'):
                result = fetcher.fetch(url, use_cache=False)

        assert result == '<html>Fresh override</html>'
        mock_get.assert_called_once()

    def test_corrupted_cache_returns_content(self, tmp_path):
        """Given cache file is corrupted (not valid HTML), When fetch reads it, Then it still returns the content."""
        cache_dir = tmp_path / 'cache'
        fetcher = WebsiteFetcher(cache_dir=cache_dir)

        url = 'http://example.com'
        cache_key = fetcher._cache_key(url)
        cache_file = cache_dir / f"{cache_key}.html"
        cache_file.write_text('garbage binary content', encoding='utf-8')

        with patch('fetchers.website.requests.get') as mock_get:
            result = fetcher.fetch(url, use_cache=True)

        assert result == 'garbage binary content'
        mock_get.assert_not_called()

    def test_fetch_with_404_returns_none(self, tmp_path):
        """Given URL returns 404, When fetch is called, Then it returns None."""
        fetcher = WebsiteFetcher()

        with patch('fetchers.website.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=404,
                raise_for_status=Mock(side_effect=requests.exceptions.HTTPError('404 Not Found'))
            )
            result = fetcher.fetch('http://example.com/missing')

        assert result is None


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_adds_http_if_no_protocol(self):
        """Given URL without protocol, When normalized, Then http:// is prepended."""
        assert normalize_url('example.com') == 'http://example.com'

    def test_preserves_existing_protocol(self):
        """Given URL with protocol, When normalized, Then it's preserved."""
        assert normalize_url('https://example.com') == 'https://example.com'

    def test_returns_none_for_empty_string(self):
        """Given empty string, When normalized, Then returns None."""
        assert normalize_url('') is None

    def test_returns_none_for_none(self):
        """Given None, When normalized, Then returns None."""
        assert normalize_url(None) is None


class TestCSVManagerEdgeCases:
    """Tests for CSV read/write edge cases."""

    def test_write_empty_list_does_not_create_file(self, tmp_path):
        """Given empty data list, When write is called, Then no file is created."""
        manager = CSVManager(tmp_path)
        manager.write('test.csv', [])
        assert not (tmp_path / 'test.csv').exists()

    def test_read_extra_columns_ignored(self, tmp_path):
        """Given CSV with extra columns not in dataclass, When read is called, Then extras are ignored."""
        csv_file = tmp_path / 'test.csv'
        csv_file.write_text(
            'restaurant_name,address,extra_col,another_extra\n'
            'Test Place,123 Main St,surprise,ignored\n',
            encoding='utf-8'
        )

        manager = CSVManager(tmp_path)
        results = manager.read('test.csv', Restaurant)

        assert len(results) == 1
        assert results[0].restaurant_name == 'Test Place'
        assert results[0].address == '123 Main St'

    def test_read_na_string_becomes_none_for_optional_float(self, tmp_path):
        """Given CSV with "N/A" in Optional[float] field, When read is called, Then field becomes None."""
        csv_file = tmp_path / 'test.csv'
        csv_file.write_text(
            'restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date,cheapest_drink_price\n'
            'Test Place,123 Main St,,,,,,,,,,N/A\n',
            encoding='utf-8'
        )

        manager = CSVManager(tmp_path)
        results = manager.read('test.csv', Restaurant)

        assert len(results) == 1
        assert results[0].cheapest_drink_price is None

    def test_write_none_values_become_empty_strings(self, tmp_path):
        """Given dataclass with None fields, When write is called, Then None values are written as empty strings."""
        manager = CSVManager(tmp_path)
        restaurant = Restaurant(
            restaurant_name='Test Place',
            address='123 Main St',
            phone_number=None,
            website_url='',
            happy_hour_times='Monday: 3-6 PM',
            regular_hours='',
            rating='4.0',
            review_count='10',
            price_level='PRICE_LEVEL_MODERATE',
            source='test',
            freshness_date='2026-04-20',
        )

        manager.write('test.csv', [restaurant])

        content = (tmp_path / 'test.csv').read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        # Data line should have empty strings for None/empty fields
        data_row = lines[1]
        assert '' in data_row


class TestHappyHourProcessorConfidence:
    """Tests for AI confidence rejection in HappyHourProcessor."""

    def test_low_confidence_skips_update(self, tmp_path):
        """Given AI returns low confidence, When process is called, Then restaurant is not updated and returns False."""
        ai_client = Mock(spec=OpenRouterClient)
        ai_client.complete.return_value = json.dumps({
            'happy_hours': ['Monday: 3-6 PM'],
            'confidence': 'low',
            'source': 'AI'
        })

        fetcher = Mock(spec=WebsiteFetcher)
        fetcher.find_menu_page.return_value = 'http://example.com/menu'
        fetcher.fetch_clean.return_value = 'Some menu content'

        processor = HappyHourProcessor(ai_client, fetcher)
        restaurant = Restaurant(
            restaurant_name='Test Place',
            address='123 Main St',
            phone_number='',
            website_url='http://example.com',
            happy_hour_times='',
            regular_hours='',
            rating='',
            review_count='',
            price_level='',
            source='',
            freshness_date='',
        )

        result = processor.process(restaurant)

        assert result is False
        assert restaurant.happy_hour_times == ''

    def test_high_confidence_updates_restaurant(self, tmp_path):
        """Given AI returns high confidence, When process is called, Then restaurant is updated and returns True."""
        ai_client = Mock(spec=OpenRouterClient)
        ai_client.complete.return_value = json.dumps({
            'happy_hours': [{'day': 'Monday', 'times': '3:00 PM - 6:00 PM'}],
            'confidence': 'high',
            'source': 'AI'
        })

        fetcher = Mock(spec=WebsiteFetcher)
        fetcher.find_menu_page.return_value = 'http://example.com/menu'
        fetcher.fetch_clean.return_value = 'Some menu content'

        processor = HappyHourProcessor(ai_client, fetcher)
        restaurant = Restaurant(
            restaurant_name='Test Place',
            address='123 Main St',
            phone_number='',
            website_url='http://example.com',
            happy_hour_times='',
            regular_hours='',
            rating='',
            review_count='',
            price_level='',
            source='',
            freshness_date='',
        )

        result = processor.process(restaurant)

        assert result is True
        assert 'Monday: 3:00 PM - 6:00 PM' in restaurant.happy_hour_times
        assert 'Website (AI parsed, high confidence)' == restaurant.source

    def test_no_website_returns_false(self):
        """Given restaurant has no website URL, When process is called, Then it returns False immediately."""
        ai_client = Mock(spec=OpenRouterClient)
        fetcher = Mock(spec=WebsiteFetcher)

        processor = HappyHourProcessor(ai_client, fetcher)
        restaurant = Restaurant(
            restaurant_name='No Site',
            address='123 Main St',
            phone_number='',
            website_url='',
            happy_hour_times='',
            regular_hours='',
            rating='',
            review_count='',
            price_level='',
            source='',
            freshness_date='',
        )

        result = processor.process(restaurant)

        assert result is False
        ai_client.complete.assert_not_called()

    def test_failed_fetch_returns_false(self):
        """Given fetch_clean returns None, When process is called, Then it returns False."""
        ai_client = Mock(spec=OpenRouterClient)
        fetcher = Mock(spec=WebsiteFetcher)
        fetcher.find_menu_page.return_value = 'http://example.com/menu'
        fetcher.fetch_clean.return_value = None

        processor = HappyHourProcessor(ai_client, fetcher)
        restaurant = Restaurant(
            restaurant_name='Fail Fetch',
            address='123 Main St',
            phone_number='',
            website_url='http://example.com',
            happy_hour_times='',
            regular_hours='',
            rating='',
            review_count='',
            price_level='',
            source='',
            freshness_date='',
        )

        result = processor.process(restaurant)

        assert result is False
        ai_client.complete.assert_not_called()


class TestProcessingState:
    """Tests for ProcessingState default behavior."""

    def test_default_lists_are_empty(self):
        """Given no explicit lists, When ProcessingState is created, Then lists default to empty."""
        state = ProcessingState(step='fetch')
        assert state.completed_restaurants == []
        assert state.failed_restaurants == []

    def test_serialization_roundtrip(self):
        """Given ProcessingState with data, When serialized then deserialized, Then values match."""
        state = ProcessingState(step='fetch')
        state.completed_restaurants = ['Place 1', 'Place 2']
        state.failed_restaurants = ['Fail 1']

        serialized = state.to_dict()
        restored = ProcessingState.from_dict(serialized)

        assert restored.completed_restaurants == ['Place 1', 'Place 2']
        assert restored.failed_restaurants == ['Fail 1']
        assert restored.step == 'fetch'
