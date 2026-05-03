"""
Tests for orchestrator AI modules.
"""
import pytest
from scripts.ai.prompts import format_happy_hour_prompt, format_menu_prompt


def test_happy_hour_prompt_formatting():
    """Test happy hour prompt includes website content."""
    text = "Monday-Friday: 3-6 PM happy hour"
    prompt = format_happy_hour_prompt(text)
    
    assert "Monday-Friday: 3-6 PM happy hour" in prompt
    assert "happy hour schedule" in prompt
    assert "JSON" in prompt


def test_menu_prompt_formatting():
    """Test menu prompt includes restaurant name and content."""
    name = "Test Restaurant"
    text = "$5 beers, $1 wings"
    prompt = format_menu_prompt(name, text)
    
    assert "Test Restaurant" in prompt
    assert "$5 beers, $1 wings" in prompt
    assert "happy hour" in prompt.lower()
    assert "wine-by-the-glass" in prompt
    assert "CHEAPEST qualifying happy-hour drink" in prompt
    assert "short_summary" in prompt


def test_menu_prompt_under_15_words():
    """Test menu prompt asks for short summary."""
    prompt = format_menu_prompt("Test", "content")
    assert "UNDER 15 words" in prompt


def test_menu_prompt_includes_schedule_when_provided():
    """Known happy hour times are injected for model context."""
    prompt = format_menu_prompt(
        "Bar",
        "$6 drafts",
        happy_hour_times="Monday: 4:00 PM - 6:00 PM",
    )
    assert "Monday: 4:00 PM - 6:00 PM" in prompt
    assert "Known happy hour schedule" in prompt


def test_menu_prompt_schedule_optional_empty():
    prompt = format_menu_prompt("Bar", "content", happy_hour_times=None)
    assert "Known happy hour schedule" not in prompt
