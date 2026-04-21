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
