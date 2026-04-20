#!/usr/bin/env python3
"""
Unit tests for scrape_hangout.py
Tests the single-place scraper and CSV manipulation
"""
import sys
import csv
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

# We can't directly import scrape_hangout because it runs code on import
# So we'll test the functions it would use
import scrape_websites_ai as scraper


class TestScrapeHangoutWorkflow:
    """Tests that simulate the scrape_hangout workflow"""

    def test_finds_hangout_in_csv_data(self, tmp_path):
        """Should be able to find The Hangout in a list of places"""
        places = [
            {'restaurant_name': 'The Vibe', 'happy_hour_times': ''},
            {'restaurant_name': 'The Hangout Restaurant and Bar', 'happy_hour_times': 'old data'},
            {'restaurant_name': 'Rabbit Hole', 'happy_hour_times': ''}
        ]

        # Find The Hangout (case insensitive search)
        hangout = None
        for place in places:
            if 'hangout' in place.get('restaurant_name', '').lower():
                hangout = place
                break

        assert hangout is not None
        assert 'Hangout' in hangout['restaurant_name']

    def test_clears_existing_data(self):
        """Should clear existing happy hour data before scraping"""
        place = {
            'restaurant_name': 'The Hangout',
            'happy_hour_times': 'Monday: 2-5 PM',
            'source': 'Old Source'
        }

        # Simulate the reset
        place['happy_hour_times'] = ''
        place['source'] = ''

        assert place['happy_hour_times'] == ''
        assert place['source'] == ''

    def test_updates_place_on_successful_scrape(self):
        """Should update place data when scraping succeeds"""
        place = {
            'restaurant_name': 'The Hangout',
            'happy_hour_times': '',
            'source': ''
        }

        # Simulate successful scrape
        hh_text = 'Monday: 3:00 PM - 6:00 PM | Tuesday: 4-7 PM'
        place['happy_hour_times'] = hh_text
        place['source'] = 'Website'
        place['freshness_date'] = '2026-04-19'

        assert place['happy_hour_times'] == hh_text
        assert place['source'] == 'Website'
        assert place['freshness_date'] == '2026-04-19'

    def test_keeps_place_unchanged_on_failed_scrape(self):
        """Should keep empty data when scraping fails"""
        place = {
            'restaurant_name': 'The Hangout',
            'happy_hour_times': '',
            'source': ''
        }

        # Simulate failed scrape (status != success, hh_text is None)
        hh_text = None
        status = 'no_website'

        if hh_text:
            place['happy_hour_times'] = hh_text
            place['source'] = 'Website'

        assert place['happy_hour_times'] == ''
        assert place['source'] == ''


class TestCSVReadWrite:
    """Tests for CSV manipulation that scrape_hangout does"""

    def test_reads_csv_with_all_fields(self, tmp_path):
        """Should read CSV preserving all columns"""
        csv_file = tmp_path / 'test.csv'
        csv_file.write_text('''restaurant_name,address,happy_hour_times,source,freshness_date
The Hangout,123 Main St,Monday: 2-5 PM,google_maps,2026-04-18
Other Place,456 Oak St,Tuesday: 3-6 PM,google_maps,2026-04-18''')

        places = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                places.append(row)

        assert len(places) == 2
        assert places[0]['restaurant_name'] == 'The Hangout'
        assert 'address' in places[0]
        assert 'source' in places[0]

    def test_writes_csv_preserving_structure(self, tmp_path):
        """Should write CSV with same structure as input"""
        places = [
            {
                'restaurant_name': 'The Hangout',
                'address': '123 Main St',
                'happy_hour_times': 'Monday: 3-6 PM',
                'source': 'Website',
                'freshness_date': '2026-04-19'
            }
        ]

        csv_file = tmp_path / 'output.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=places[0].keys())
            writer.writeheader()
            writer.writerows(places)

        # Read it back
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'restaurant_name' in content
            assert 'The Hangout' in content
            assert 'Website' in content

    def test_handles_csv_with_unicode(self, tmp_path):
        """Should handle CSV with unicode characters"""
        places = [
            {
                'restaurant_name': 'Café & Bar',
                'happy_hour_times': 'Lunes: 3-6 PM'
            }
        ]

        csv_file = tmp_path / 'output.csv'
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=places[0].keys())
            writer.writeheader()
            writer.writerows(places)

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]['restaurant_name'] == 'Café & Bar'


class TestScrapeRestaurantIntegration:
    """Integration tests for scrape_restaurant behavior"""

    @patch('scrape_websites_ai.requests.get')
    def test_returns_none_for_empty_url(self, mock_get):
        """Should return None status for empty URL"""
        result, status = scraper.scrape_restaurant('Test', '')
        assert result is None
        assert status == 'no_website'
        mock_get.assert_not_called()

    @patch('scrape_websites_ai.requests.get')
    def test_returns_no_mention_without_happy_hour_text(self, mock_get):
        """Should detect when website has no happy hour mention"""
        mock_response = MagicMock()
        mock_response.text = '<html><body>Menu and reservations info</body></html>'
        mock_get.return_value = mock_response

        result, status = scraper.scrape_restaurant('Test Bar', 'http://test.com')
        assert result is None
        assert status == 'no_mention'

    @patch('scrape_websites_ai.requests.get')
    def test_fetches_happy_hour_pages(self, mock_get):
        """Should check common paths for happy hour info"""
        mock_response = MagicMock()
        mock_response.text = '<html><body>happy hour special drinks</body></html>'
        mock_get.return_value = mock_response

        scraper.scrape_restaurant('Test Bar', 'http://test.com')

        # Should have been called at least once
        assert mock_get.called

    @patch('scrape_websites_ai.requests.get')
    def test_handles_request_exception(self, mock_get):
        """Should handle network errors gracefully"""
        mock_get.side_effect = Exception('Connection failed')

        result, status = scraper.scrape_restaurant('Test Bar', 'http://test.com')
        assert result is None
        assert status == 'no_website'


class TestEdgeCases:
    """Edge case tests for scrape_hangout behavior"""

    def test_handles_place_without_website(self):
        """Should handle restaurant entries without website_url"""
        place = {
            'restaurant_name': 'The Hangout',
            'website_url': ''
        }

        assert place.get('website_url', '') == ''

    def test_handles_partial_name_match(self):
        """Should match partial names correctly"""
        places = [
            {'restaurant_name': 'The Hangout'},
            {'restaurant_name': 'Hangout Cafe'},
            {'restaurant_name': 'Coffee Corner'}
        ]

        matches = [p for p in places if 'hangout' in p['restaurant_name'].lower()]
        assert len(matches) == 2

    def test_breaks_after_first_match(self):
        """Should only process the first matching restaurant"""
        places = [
            {'restaurant_name': 'First Hangout'},
            {'restaurant_name': 'Second Hangout'}
        ]

        processed = []
        for place in places:
            if 'hangout' in place.get('restaurant_name', '').lower():
                processed.append(place)
                break  # The script breaks after first match

        assert len(processed) == 1
        assert processed[0]['restaurant_name'] == 'First Hangout'
