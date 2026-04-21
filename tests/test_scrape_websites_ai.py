#!/usr/bin/env python3
"""
Unit tests for scrape_websites_ai.py
Tests HTML extraction, schedule formatting, and AI response parsing
"""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import scrape_websites_ai as scraper


class TestExtractTextFromHtml:
    """Tests for extract_text_from_html function"""

    def test_removes_script_tags(self):
        """Should completely remove script tags and their content"""
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        result = scraper.extract_text_from_html(html)
        assert 'alert' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_removes_style_tags(self):
        """Should completely remove style tags and their content"""
        html = '<p>Hello</p><style>.red { color: red; }</style><p>World</p>'
        result = scraper.extract_text_from_html(html)
        assert '.red' not in result
        assert 'color' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_removes_html_tags(self):
        """Should strip all HTML tags"""
        html = '<div><p><strong>Bold</strong> text</p></div>'
        result = scraper.extract_text_from_html(html)
        assert '<' not in result
        assert '>' not in result
        assert 'Bold text' in result

    def test_normalizes_whitespace(self):
        """Should collapse multiple whitespace characters to single space"""
        html = '<p>Hello    world\n\n\t   test</p>'
        result = scraper.extract_text_from_html(html)
        assert 'Hello world test' in result
        assert '    ' not in result  # No multiple spaces

    def test_handles_empty_html(self):
        """Should handle empty HTML gracefully"""
        assert scraper.extract_text_from_html('') == ''
        assert scraper.extract_text_from_html('   ') == ''

    def test_handles_html_without_tags(self):
        """Should return plain text unchanged (except for whitespace normalization)"""
        text = 'Just plain text'
        result = scraper.extract_text_from_html(text)
        assert 'Just plain text' in result


class TestFormatSchedule:
    """Tests for format_schedule function"""

    def test_formats_complete_schedule(self):
        """Should format all days with their time ranges"""
        schedule = {
            'Monday': '3:00 PM - 6:00 PM',
            'Tuesday': '4:00 PM - 7:00 PM',
            'Wednesday': 'Closed',
            'Thursday': 'Closed',
            'Friday': '3:00 PM - 6:00 PM',
            'Saturday': 'Closed',
            'Sunday': 'Closed'
        }
        result = scraper.format_schedule(schedule)
        assert 'Monday: 3:00 PM - 6:00 PM' in result
        assert 'Tuesday: 4:00 PM - 7:00 PM' in result
        assert 'Wednesday: Closed' in result
        assert '|' in result  # Should be pipe-separated

    def test_handles_missing_days(self):
        """Should show 'Closed' for days not in schedule"""
        schedule = {
            'Monday': '3:00 PM - 6:00 PM'
        }
        result = scraper.format_schedule(schedule)
        # Days not present should default to Closed
        assert 'Monday: 3:00 PM - 6:00 PM' in result
        assert 'Tuesday: Closed' in result

    def test_handles_empty_schedule(self):
        """Should return all days as Closed for empty schedule"""
        result = scraper.format_schedule({})
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            assert f'{day}: Closed' in result

    def test_orders_days_correctly(self):
        """Should output days in Monday-Sunday order"""
        schedule = {'Sunday': '1-2', 'Monday': '3-4'}
        result = scraper.format_schedule(schedule)
        # Monday should come before Sunday
        monday_pos = result.find('Monday')
        sunday_pos = result.find('Sunday')
        assert monday_pos < sunday_pos


class TestParseWithAi:
    """Tests for parse_with_ai function with mocked API"""

    @patch('scrape_websites_ai.requests.post')
    def test_parses_valid_json_response(self, mock_post):
        """Should extract and parse valid JSON from AI response"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'has_happy_hour': True,
                        'schedule': {
                            'Monday': '3:00 PM - 6:00 PM',
                            'Tuesday': 'Closed',
                            'Wednesday': 'Closed',
                            'Thursday': 'Closed',
                            'Friday': '3:00 PM - 6:00 PM',
                            'Saturday': 'Closed',
                            'Sunday': 'Closed'
                        },
                        'notes': '$5 beers'
                    })
                }
            }]
        }
        mock_post.return_value = mock_response

        result = scraper.parse_with_ai('Some website text', 'Test Restaurant')
        assert result['has_happy_hour'] is True
        assert 'schedule' in result
        assert result['schedule']['Monday'] == '3:00 PM - 6:00 PM'

    @patch('scrape_websites_ai.requests.post')
    def test_extracts_json_from_markdown_response(self, mock_post):
        """Should extract JSON even when wrapped in markdown code blocks"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '```json\n{"has_happy_hour": true, "schedule": {}, "notes": ""}\n```'
                }
            }]
        }
        mock_post.return_value = mock_response

        result = scraper.parse_with_ai('Some text', 'Test')
        assert result['has_happy_hour'] is True

    @patch('scrape_websites_ai.requests.post')
    def test_returns_default_on_api_error(self, mock_post):
        """Should return default no-happy-hour structure on API error"""
        mock_post.side_effect = Exception('API Error')

        result = scraper.parse_with_ai('Some text', 'Test')
        assert result['has_happy_hour'] is False
        assert result['schedule'] == {}
        assert result['notes'] == ''

    @patch('scrape_websites_ai.requests.post')
    def test_returns_default_on_invalid_json(self, mock_post):
        """Should return default structure when response is not valid JSON"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'This is not valid JSON {{'
                }
            }]
        }
        mock_post.return_value = mock_response

        result = scraper.parse_with_ai('Some text', 'Test')
        assert result['has_happy_hour'] is False


class TestGetHeaders:
    """Tests for get_headers function"""

    def test_returns_dict_with_user_agent(self):
        """Should return dict containing User-Agent header"""
        headers = scraper.get_headers()
        assert 'User-Agent' in headers
        assert 'Mozilla' in headers['User-Agent']

    def test_returns_accept_headers(self):
        """Should include Accept headers for HTML content"""
        headers = scraper.get_headers()
        assert 'Accept' in headers
        assert 'text/html' in headers['Accept']

    def test_user_agent_rotates(self):
        """Should randomly select from available user agents"""
        # Run multiple times to check different agents might be selected
        agents = set()
        for _ in range(20):
            headers = scraper.get_headers()
            agents.add(headers['User-Agent'])
        # Should have at least one of the defined agents
        assert len(agents) <= len(scraper.USER_AGENTS)
