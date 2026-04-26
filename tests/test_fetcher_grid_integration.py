"""
Tests for fetcher type filtering and place_id capture.
"""
import pytest
from scripts.fetchers.google_places import (
    convert_to_restaurant,
    search_places_text,
    search_places_paginated,
)
from scripts.fetchers.grid import should_exclude_place


def test_convert_to_restaurant_captures_place_id():
    """Test that convert_to_restaurant extracts the place id."""
    place_data = {
        'id': 'ChIJabc123',
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.place_id == "ChIJabc123"


def test_convert_to_restaurant_missing_place_id():
    """Test that convert_to_restaurant handles missing id."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.place_id == ""


def test_should_exclude_place_cafe():
    """Test pure cafe is excluded."""
    assert should_exclude_place(["cafe", "coffee_shop"]) is True


def test_should_exclude_place_bar_kept():
    """Test bar is not excluded."""
    assert should_exclude_place(["bar", "restaurant"]) is False


def test_should_exclude_place_mixed():
    """Test cafe + restaurant is kept because restaurant is not excluded."""
    assert should_exclude_place(["cafe", "restaurant"]) is False
