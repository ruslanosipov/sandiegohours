#!/usr/bin/env python3
"""
Tests for API failure handling in google_places.py and openrouter.py
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from fetchers.google_places import (
    get_place_details_new,
    parse_secondary_opening_hours,
    search_places_text,
)
from ai.openrouter import OpenRouterClient


class TestGetPlaceDetailsNew:
    """Tests for get_place_details_new API failure handling."""

    @patch('fetchers.google_places.requests.get')
    def test_returns_none_on_500_error(self, mock_get):
        """Given API returns 500, When get_place_details_new is called, Then it returns None."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_place_details_new('place_123', 'test_key')
        assert result is None

    @patch('fetchers.google_places.requests.get')
    def test_returns_none_on_429_rate_limit(self, mock_get):
        """Given API returns 429, When called, Then it returns None."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = get_place_details_new('place_123', 'test_key')
        assert result is None

    @patch('fetchers.google_places.requests.get')
    def test_returns_json_on_success(self, mock_get):
        """Given API returns 200 with data, When called, Then it returns parsed JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'place_123', 'displayName': {'text': 'Test'}}
        mock_get.return_value = mock_response

        result = get_place_details_new('place_123', 'test_key')
        assert result == {'id': 'place_123', 'displayName': {'text': 'Test'}}


class TestParseSecondaryOpeningHours:
    """Tests for parse_secondary_opening_hours edge cases."""

    def test_returns_none_for_empty_list(self):
        """Given empty secondary_hours list, When parsed, Then returns None."""
        assert parse_secondary_opening_hours([]) is None

    def test_returns_none_for_non_list_input(self):
        """Given non-list input, When parsed, Then returns None."""
        assert parse_secondary_opening_hours(None) is None

    def test_skips_non_happy_hour_types(self):
        """Given DRIVE_THROUGH type only, When parsed, Then returns None."""
        hours = [{'secondaryHoursType': 'DRIVE_THROUGH', 'weekdayDescriptions': ['Mon: 8-10']},]
        assert parse_secondary_opening_hours(hours) is None

    def test_returns_formatted_happy_hours(self):
        """Given HAPPY_HOUR type with descriptions, When parsed, Then returns pipe-joined string."""
        hours = [{
            'secondaryHoursType': 'HAPPY_HOUR',
            'weekdayDescriptions': ['Monday: 3:00 PM - 6:00 PM', 'Tuesday: 3:00 PM - 6:00 PM']
        }]
        result = parse_secondary_opening_hours(hours)
        assert result == 'Monday: 3:00 PM - 6:00 PM | Tuesday: 3:00 PM - 6:00 PM'

    def test_returns_none_for_happy_hour_with_empty_descriptions(self):
        """Given HAPPY_HOUR type with empty descriptions, When parsed, Then returns None."""
        hours = [{'secondaryHoursType': 'HAPPY_HOUR', 'weekdayDescriptions': []},]
        assert parse_secondary_opening_hours(hours) is None


class TestSearchPlacesText:
    """Tests for search_places_text API failure handling."""

    @patch('fetchers.google_places.requests.post')
    def test_returns_empty_list_on_api_error(self, mock_post):
        """Given API returns non-200, When search_places_text is called, Then returns empty list and no token."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        results, token = search_places_text('32.71,-117.16', keyword='restaurant', api_key='test_key')
        assert results == []
        assert token is None

    @patch('fetchers.google_places.requests.post')
    def test_returns_results_and_next_page_token_on_success(self, mock_post):
        """Given API returns results with nextPageToken, When called, Then returns both."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'places': [
                {'id': 'place1', 'displayName': {'text': 'Place 1'}},
                {'id': 'place2', 'displayName': {'text': 'Place 2'}},
            ],
            'nextPageToken': 'token_123'
        }
        mock_post.return_value = mock_response

        results, token = search_places_text('32.71,-117.16', keyword='restaurant', api_key='test_key')
        assert len(results) == 2
        assert token == 'token_123'


class TestOpenRouterClientRetries:
    """Tests for OpenRouterClient retry and error handling."""

    def test_rate_limit_429_retries_with_backoff(self):
        """Given 429 on first two attempts, When complete is called, Then retries and succeeds on third."""
        client = OpenRouterClient('fake_key', max_retries=3)

        responses = [
            Mock(status_code=429, raise_for_status=Mock()),
            Mock(status_code=429, raise_for_status=Mock()),
            Mock(
                status_code=200,
                raise_for_status=Mock(),
                json=Mock(return_value={
                    'choices': [{'message': {'content': 'Success'}}]
                })
            ),
        ]

        with patch('ai.openrouter.requests.post') as mock_post:
            mock_post.side_effect = responses
            with patch('ai.openrouter.time.sleep') as mock_sleep:
                result = client.complete('test prompt')

        assert result == 'Success'
        assert mock_post.call_count == 3
        # Check backoff waits: 2^1=2s, 2^2=4s
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    def test_request_exception_retries_then_raises(self):
        """Given RequestException on all attempts, When complete is called, Then raises Exception after max retries."""
        client = OpenRouterClient('fake_key', max_retries=2)

        with patch('ai.openrouter.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException('Connection timeout')
            with patch('ai.openrouter.time.sleep'):
                with pytest.raises(Exception, match='OpenRouter API failed after 2 retries'):
                    client.complete('test prompt')

        assert mock_post.call_count == 2

    def test_success_on_first_attempt_no_retries(self):
        """Given success on first attempt, When complete is called, Then returns immediately without sleeping."""
        client = OpenRouterClient('fake_key', max_retries=3)

        with patch('ai.openrouter.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                raise_for_status=Mock(),
                json=Mock(return_value={
                    'choices': [{'message': {'content': 'Quick success'}}]
                })
            )
            with patch('ai.openrouter.time.sleep') as mock_sleep:
                result = client.complete('test prompt')

        assert result == 'Quick success'
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()
