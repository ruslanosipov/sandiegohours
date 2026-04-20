#!/usr/bin/env python3
"""
Unit tests for apply_overrides.py
Tests CSV parsing, override application, and edge cases
"""
import sys
import csv
import tempfile
import os
from pathlib import Path
from io import StringIO
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import apply_overrides as overrides


class TestLoadManualOverrides:
    """Tests for load_manual_overrides function"""

    def test_loads_valid_csv(self, tmp_path, monkeypatch):
        """Should load overrides from a valid CSV file"""
        # Create a temp overrides file
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Test Restaurant,Monday: 3-6 PM,Manual,2026-04-19
Another Place,Tuesday: 4-7 PM,Manual,2026-04-19''')

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        result = overrides.load_manual_overrides()
        assert len(result) == 2
        assert 'test restaurant' in result  # lowercase key
        assert result['test restaurant']['happy_hour_times'] == 'Monday: 3-6 PM'

    def test_handles_missing_file(self, tmp_path, monkeypatch):
        """Should return empty dict when file doesn't exist"""
        monkeypatch.chdir(tmp_path)
        result = overrides.load_manual_overrides()
        assert result == {}

    def test_empty_restaurant_name_skipped(self, tmp_path, monkeypatch):
        """Should skip rows with empty restaurant names"""
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
,Monday: 3-6 PM,Manual,2026-04-19
Valid Name,Tuesday: 4-7 PM,Manual,2026-04-19''')

        monkeypatch.chdir(tmp_path)
        result = overrides.load_manual_overrides()
        assert len(result) == 1
        assert 'valid name' in result

    def test_normalizes_keys_to_lowercase(self, tmp_path, monkeypatch):
        """Should normalize restaurant names to lowercase for matching"""
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
UPPER CASE,Monday: 3-6 PM,Manual,2026-04-19
MiXeD CaSe,Tuesday: 4-7 PM,Manual,2026-04-19''')

        monkeypatch.chdir(tmp_path)
        result = overrides.load_manual_overrides()
        assert 'upper case' in result
        assert 'mixed case' in result

    def test_preserves_all_fields(self, tmp_path, monkeypatch):
        """Should preserve all override fields"""
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Test Place,Monday: 3-6 PM,Manual,2026-04-19''')

        monkeypatch.chdir(tmp_path)
        result = overrides.load_manual_overrides()
        entry = result['test place']
        assert entry['happy_hour_times'] == 'Monday: 3-6 PM'
        assert entry['source'] == 'Manual'
        assert entry['freshness_date'] == '2026-04-19'


class TestMainFunctionality:
    """Integration tests for main override application logic"""

    def test_applies_override_to_matching_restaurant(self, tmp_path, monkeypatch):
        """Should update happy hour data when restaurant name matches"""
        monkeypatch.chdir(tmp_path)

        # Create override file
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Kairoa Brewing Company,Wednesday: 4:00 - 6:00 PM,Manual,2026-04-19''')

        # Create main CSV
        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date
Kairoa Brewing Company,123 Main St,,,,,,,,google_maps,
Other Restaurant,456 Oak St,,,Monday: 2-5 PM,,,,,google_maps,''')

        # Run main function
        overrides.main()

        # Verify the CSV was updated
        with open(main_csv, 'r') as f:
            content = f.read()
            assert 'Wednesday: 4:00 - 6:00 PM' in content
            assert 'Manual' in content
            # Other restaurant should remain unchanged
            assert 'Other Restaurant' in content

    def test_preserves_original_when_no_override(self, tmp_path, monkeypatch):
        """Should keep original data when no override exists"""
        monkeypatch.chdir(tmp_path)

        # Create empty override file
        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
NonExistent Place,Monday: 3-6 PM,Manual,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date
Existing Place,123 Main St,,,Monday: 2-5 PM,,,,,google_maps,''')

        overrides.main()

        with open(main_csv, 'r') as f:
            content = f.read()
            assert 'Monday: 2-5 PM' in content  # Original preserved
            assert 'google_maps' in content

    def test_case_insensitive_matching(self, tmp_path, monkeypatch):
        """Should match restaurant names case-insensitively"""
        monkeypatch.chdir(tmp_path)

        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
LOWERCASE NAME,Monday: 3-6 PM,Manual,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date\nlowercase name,123 Main St,,,,,,,,google_maps,\nUPPERCASE NAME,456 Oak St,,,,,,,,google_maps,''')

        overrides.main()

        with open(main_csv, 'r') as f:
            content = f.read()
            assert 'Monday: 3-6 PM' in content
            assert 'Manual' in content

    def test_preserves_all_csv_columns(self, tmp_path, monkeypatch):
        """Should preserve all columns in the output CSV"""
        monkeypatch.chdir(tmp_path)

        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Test Place,Monday: 3-6 PM,Manual,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date\nTest Place,123 Main St,555-1234,http://test.com,,,,,,google_maps,''')

        overrides.main()

        with open(main_csv, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            # Header should have all columns
            assert 'restaurant_name' in lines[0]
            assert 'address' in lines[0]
            assert 'phone' in lines[0]
            assert 'website' in lines[0]


class TestEdgeCases:
    """Edge case tests"""

    def test_handles_empty_main_csv(self, tmp_path, monkeypatch, capsys):
        """Should handle empty main CSV gracefully"""
        monkeypatch.chdir(tmp_path)

        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Test Place,Monday: 3-6 PM,Manual,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('restaurant_name,address,happy_hour_times,source\n')

        # Should not raise exception
        overrides.main()

    def test_handles_whitespace_in_names(self, tmp_path, monkeypatch):
        """Should handle restaurant names with extra whitespace"""
        monkeypatch.chdir(tmp_path)

        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
"  Padded Name  ",Monday: 3-6 PM,Manual,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date\nPadded Name,123 Main St,,,,,,,,google_maps,''')

        overrides.main()

        with open(main_csv, 'r') as f:
            content = f.read()
            assert 'Manual' in content  # Override was applied

    def test_handles_missing_fields_in_override(self, tmp_path, monkeypatch):
        """Should handle override rows with missing fields"""
        monkeypatch.chdir(tmp_path)

        overrides_csv = tmp_path / 'manual_overrides.csv'
        overrides_csv.write_text('''restaurant_name,happy_hour_times,source,freshness_date
Test Place,Monday: 3-6 PM,,2026-04-19''')

        main_csv = tmp_path / 'public' / 'happy_hours.csv'
        main_csv.parent.mkdir()
        main_csv.write_text('''restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,rating,review_count,price_level,source,freshness_date\nTest Place,123 Main St,,,,,,,,google_maps,''')

        overrides.main()

        with open(main_csv, 'r') as f:
            content = f.read()
            # Should use current date for missing freshness_date
            assert '2026-04-19' in content

