"""
Tests for Google Maps URL and generative summary fields.
"""
import pytest
from scripts.storage.models import Restaurant
from scripts.storage.csv_manager import CSVManager
from scripts.fetchers.google_places import convert_to_restaurant


def test_restaurant_model_has_google_maps_url():
    """Test Restaurant dataclass includes google_maps_url field."""
    r = Restaurant(
        restaurant_name="Test Bar",
        address="123 Main St",
        google_maps_url="https://www.google.com/maps/place/Test+Bar"
    )
    assert r.google_maps_url == "https://www.google.com/maps/place/Test+Bar"


def test_restaurant_model_has_generative_summary():
    """Test Restaurant dataclass includes generative_summary field."""
    r = Restaurant(
        restaurant_name="Test Bar",
        address="123 Main St",
        generative_summary="A cozy neighborhood bar with craft cocktails and live music."
    )
    assert r.generative_summary == "A cozy neighborhood bar with craft cocktails and live music."


def test_restaurant_model_default_values():
    """Test new fields have empty string defaults."""
    r = Restaurant(
        restaurant_name="Test Bar",
        address="123 Main St"
    )
    assert r.google_maps_url == ""
    assert r.generative_summary == ""


def test_convert_to_restaurant_extracts_place_id():
    """Test convert_to_restaurant extracts id from API response."""
    place_data = {
        'id': 'ChIJabc123',
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.place_id == "ChIJabc123"


def test_convert_to_restaurant_handles_missing_place_id():
    """Test convert_to_restaurant handles missing id."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.place_id == ""


def test_convert_to_restaurant_extracts_google_maps_url():
    """Test convert_to_restaurant extracts googleMapsUri from API response."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
        'googleMapsUri': 'https://www.google.com/maps/place/Test+Restaurant',
    }

    result = convert_to_restaurant(place_data)

    assert result.google_maps_url == "https://www.google.com/maps/place/Test+Restaurant"


def test_convert_to_restaurant_extracts_generative_summary():
    """Test convert_to_restaurant extracts editorialSummary from API response."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
        'editorialSummary': {
            'text': 'A popular local spot known for craft beers and pub grub.'
        },
    }

    result = convert_to_restaurant(place_data)

    assert result.generative_summary == "A popular local spot known for craft beers and pub grub."


def test_convert_to_restaurant_handles_missing_google_maps_url():
    """Test convert_to_restaurant handles missing googleMapsUri."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.google_maps_url == ""


def test_convert_to_restaurant_handles_missing_generative_summary():
    """Test convert_to_restaurant handles missing generativeSummary."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
    }

    result = convert_to_restaurant(place_data)

    assert result.generative_summary == ""


def test_convert_to_restaurant_handles_empty_generative_summary():
    """Test convert_to_restaurant handles empty editorialSummary object."""
    place_data = {
        'displayName': {'text': 'Test Restaurant'},
        'formattedAddress': '123 Main St, San Diego, CA',
        'editorialSummary': {},
    }

    result = convert_to_restaurant(place_data)

    assert result.generative_summary == ""


def test_csv_manager_roundtrip_with_new_fields(tmp_path):
    """Test CSVManager can read and write restaurants with new fields."""
    manager = CSVManager(tmp_path)

    restaurants = [
        Restaurant(
            restaurant_name="Bar A",
            address="123 Main St",
            google_maps_url="https://www.google.com/maps/place/Bar+A",
            generative_summary="Great happy hour deals on tacos and margaritas."
        ),
        Restaurant(
            restaurant_name="Bar B",
            address="456 Oak St",
            google_maps_url="",
            generative_summary=""
        ),
    ]

    manager.write("test.csv", restaurants)
    result = manager.read("test.csv", Restaurant)

    assert len(result) == 2
    assert result[0].google_maps_url == "https://www.google.com/maps/place/Bar+A"
    assert result[0].generative_summary == "Great happy hour deals on tacos and margaritas."
    # Empty strings in CSV become None when read back (CSVManager behavior)
    assert result[1].google_maps_url is None
    assert result[1].generative_summary is None
