"""
Tests for orchestrator storage modules.
"""
import pytest
from pathlib import Path
import tempfile
import os

from scripts.storage.models import Restaurant, MenuData, ProcessingState
from scripts.storage.csv_manager import CSVManager


def test_restaurant_model():
    """Test Restaurant dataclass creation."""
    r = Restaurant(
        restaurant_name="Test Bar",
        address="123 Main St",
        cheapest_drink="$5 beer",
        cheapest_drink_price=5.0
    )
    
    assert r.restaurant_name == "Test Bar"
    assert r.cheapest_drink_price == 5.0


def test_restaurant_model_has_place_id():
    """Test Restaurant dataclass includes place_id field."""
    r = Restaurant(
        restaurant_name="Test Bar",
        address="123 Main St",
        place_id="ChIJ123"
    )
    assert r.place_id == "ChIJ123"


def test_restaurant_model_place_id_default():
    """Test place_id defaults to empty string."""
    r = Restaurant(restaurant_name="Test Bar", address="123 Main St")
    assert r.place_id == ""


def test_processing_state_serialization():
    """Test ProcessingState can be serialized/deserialized."""
    state = ProcessingState(
        step="parse_menus",
        completed_restaurants=["Bar A", "Bar B"],
        failed_restaurants=["Bar C"]
    )
    
    data = state.to_dict()
    restored = ProcessingState.from_dict(data)
    
    assert restored.step == "parse_menus"
    assert "Bar A" in restored.completed_restaurants
    assert "Bar C" in restored.failed_restaurants


def test_csv_manager_read_write(tmp_path):
    """Test CSVManager can read and write data."""
    manager = CSVManager(tmp_path)
    
    # Write test data
    restaurants = [
        Restaurant(restaurant_name="Bar A", address="123 Main"),
        Restaurant(restaurant_name="Bar B", address="456 Oak"),
    ]
    
    manager.write("test.csv", restaurants)
    
    # Read it back
    result = manager.read("test.csv", Restaurant)
    
    assert len(result) == 2
    assert result[0].restaurant_name == "Bar A"
    assert result[1].address == "456 Oak"


def test_csv_manager_handles_missing_file(tmp_path):
    """Test CSVManager returns empty list for missing files."""
    manager = CSVManager(tmp_path)
    result = manager.read("nonexistent.csv", Restaurant)
    
    assert result == []


def test_csv_manager_empty_strings_become_none():
    """Test that empty CSV fields become None."""
    import csv
    
    with tempfile.TemporaryDirectory() as tmp:
        # Create CSV with empty fields
        csv_path = Path(tmp) / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['restaurant_name', 'address', 'cheapest_drink'])
            writer.writerow(['Test Bar', '123 Main', ''])  # Empty cheapest_drink
        
        manager = CSVManager(Path(tmp))
        results = manager.read("test.csv", Restaurant)
        
        # Empty string should become None
        assert results[0].cheapest_drink is None


def test_csv_manager_merge_by_place_id_updates_existing(tmp_path):
    """Test merge updates existing restaurants by place_id."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(restaurant_name="Old Name", address="123 Main", place_id="ChIJ1",
                   rating="3.5", freshness_date="2024-01-01"),
    ]
    manager.write("test.csv", existing)
    
    new = [
        Restaurant(restaurant_name="New Name", address="123 Main", place_id="ChIJ1",
                   rating="4.5", freshness_date="2024-02-01"),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 1
    assert merged[0].restaurant_name == "New Name"
    assert merged[0].rating == "4.5"
    assert merged[0].freshness_date == "2024-02-01"


def test_csv_manager_merge_by_place_id_appends_new(tmp_path):
    """Test merge appends new restaurants."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(restaurant_name="Bar A", address="123 Main", place_id="ChIJ1"),
    ]
    manager.write("test.csv", existing)
    
    new = [
        Restaurant(restaurant_name="Bar B", address="456 Oak", place_id="ChIJ2",
                   freshness_date="2024-02-01"),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 2
    names = {r.restaurant_name for r in merged}
    assert names == {"Bar A", "Bar B"}


def test_csv_manager_merge_preserves_ai_fields(tmp_path):
    """Test merge preserves AI-extracted fields if new fetch doesn't have them."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(
            restaurant_name="Bar A", address="123 Main", place_id="ChIJ1",
            happy_hour_times="Monday: 3-6 PM",
            menu_summary="$1 wings, $3 beers",
            cheapest_drink="$3 beer",
            cheapest_drink_price=3.0,
            source="Website (AI parsed, high confidence)",
            freshness_date="2024-01-01",
        ),
    ]
    manager.write("test.csv", existing)
    
    # New fetch from Google has no AI fields
    new = [
        Restaurant(
            restaurant_name="Bar A", address="123 Main", place_id="ChIJ1",
            rating="4.5",
            source="Google Places API",
            freshness_date="2024-02-01",
        ),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 1
    assert merged[0].happy_hour_times == "Monday: 3-6 PM"
    assert merged[0].menu_summary == "$1 wings, $3 beers"
    assert merged[0].cheapest_drink == "$3 beer"
    assert merged[0].cheapest_drink_price == 3.0
    # source should be preserved because new source is empty? Wait, new source is "Google Places API"
    # Actually source is in the preserve list, but new has a value. Let me re-read the logic.
    # The code checks: if field in PRESERVE list and not new_val: continue
    # new source is "Google Places API" which is truthy, so it will overwrite.
    # That's actually the correct behavior - we want to know it came from Google now.
    # But for the AI-extracted fields like happy_hour_times, new is empty so it preserves.
    assert merged[0].source == "Google Places API"


def test_csv_manager_merge_overwrites_when_new_has_value(tmp_path):
    """Test merge overwrites AI fields when new fetch actually has data."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(
            restaurant_name="Bar A", address="123 Main", place_id="ChIJ1",
            happy_hour_times="Monday: 3-6 PM",
            freshness_date="2024-01-01",
        ),
    ]
    manager.write("test.csv", existing)
    
    new = [
        Restaurant(
            restaurant_name="Bar A", address="123 Main", place_id="ChIJ1",
            happy_hour_times="Tuesday: 4-7 PM",
            freshness_date="2024-02-01",
        ),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert merged[0].happy_hour_times == "Tuesday: 4-7 PM"


def test_csv_manager_merge_empty_existing(tmp_path):
    """Test merge works when no existing CSV."""
    manager = CSVManager(tmp_path)
    
    new = [
        Restaurant(restaurant_name="Bar A", address="123 Main", place_id="ChIJ1",
                   freshness_date="2024-02-01"),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 1
    assert merged[0].restaurant_name == "Bar A"


def test_csv_manager_merge_preserves_legacy_without_place_id(tmp_path):
    """Test merge preserves old entries that lack place_id (migration safety)."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(restaurant_name="Old Bar", address="789 Pine", place_id="",
                   rating="3.0", freshness_date="2024-01-01"),
    ]
    manager.write("test.csv", existing)
    
    new = [
        Restaurant(restaurant_name="New Bar", address="456 Oak", place_id="ChIJ2",
                   freshness_date="2024-02-01"),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 2
    names = {r.restaurant_name for r in merged}
    assert names == {"Old Bar", "New Bar"}


def test_csv_manager_merge_upgrades_legacy_by_name(tmp_path):
    """Test merge upgrades legacy entries when matched by restaurant_name."""
    manager = CSVManager(tmp_path)
    
    existing = [
        Restaurant(restaurant_name="Bar A", address="123 Old St", place_id="",
                   rating="3.0", happy_hour_times="Monday: 2-5 PM",
                   freshness_date="2024-01-01"),
    ]
    manager.write("test.csv", existing)
    
    new = [
        Restaurant(restaurant_name="Bar A", address="123 New St", place_id="ChIJ1",
                   rating="4.5", freshness_date="2024-02-01"),
    ]
    merged = manager.merge_by_place_id("test.csv", new, Restaurant)
    
    assert len(merged) == 1
    assert merged[0].place_id == "ChIJ1"
    assert merged[0].address == "123 New St"
    assert merged[0].rating == "4.5"
    assert merged[0].happy_hour_times == "Monday: 2-5 PM"  # preserved AI field
    assert merged[0].freshness_date == "2024-02-01"
