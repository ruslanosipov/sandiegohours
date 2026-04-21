"""
Tests for content parsers.
"""
import pytest
from scripts.parsers.content_parsers import (
    extract_json,
    parse_happy_hour_response,
    parse_menu_response,
    format_happy_hour_times
)


def test_extract_json_from_markdown():
    """Test extracting JSON from markdown code block."""
    text = """Here's the result:
```json
{"key": "value", "number": 42}
```
"""
    result = extract_json(text)
    assert result == {"key": "value", "number": 42}


def test_extract_json_from_raw():
    """Test extracting raw JSON."""
    text = '{"key": "value"}'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_extract_json_returns_none_for_invalid():
    """Test extracting None for non-JSON text."""
    text = "This is just plain text"
    result = extract_json(text)
    assert result is None


def test_parse_happy_hour_response():
    """Test parsing happy hour AI response."""
    content = '''{"happy_hours": [{"day": "Monday", "times": "3-6 PM"}], "confidence": "high"}'''
    result = parse_happy_hour_response(content)
    
    assert len(result['happy_hours']) == 1
    assert result['happy_hours'][0]['day'] == 'Monday'
    assert result['confidence'] == 'high'


def test_parse_menu_response():
    """Test parsing menu AI response."""
    content = '''{"drink": {"name": "$5 beer", "price": 5}, "food": {"name": "$1 wings", "price": 1}, "short_summary": "$1 wings, $5 beer"}'''
    result = parse_menu_response(content)
    
    assert result['drink']['name'] == '$5 beer'
    assert result['food']['price'] == 1
    assert result['short_summary'] == '$1 wings, $5 beer'


def test_format_happy_hour_times():
    """Test formatting schedule to pipe-separated string."""
    schedule = [
        {"day": "Monday", "times": "3-6 PM"},
        {"day": "Tuesday", "times": "4-7 PM"},
    ]
    result = format_happy_hour_times(schedule)
    
    assert result == "Monday: 3-6 PM | Tuesday: 4-7 PM"


def test_format_happy_hour_times_skips_empty():
    """Test formatting skips empty entries."""
    schedule = [
        {"day": "Monday", "times": "3-6 PM"},
        {"day": "", "times": ""},
    ]
    result = format_happy_hour_times(schedule)
    
    assert result == "Monday: 3-6 PM"
