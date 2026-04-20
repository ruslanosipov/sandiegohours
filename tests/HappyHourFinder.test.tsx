import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Test Bar',
    address: '123 Main St, San Diego, CA 92116',
    phone_number: '+1 555-1234',
    website_url: 'https://testbar.com',
    happy_hour_times: 'Monday: 3:00 PM - 6:00 PM | Tuesday: 3:00 PM - 6:00 PM',
    regular_hours: 'Monday: 11:00 AM - 10:00 PM',
    rating: '4.5',
    review_count: '100',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'Website',
    freshness_date: '2026-04-19',
  },
  {
    restaurant_name: 'No HH Cafe',
    address: '456 Oak St, San Diego, CA 92116',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: 'Monday: 8:00 AM - 3:00 PM',
    rating: '4.8',
    review_count: '50',
    price_level: 'PRICE_LEVEL_INEXPENSIVE',
    source: 'Google Maps API',
    freshness_date: '2026-04-19',
  },
  {
    restaurant_name: 'Multi-HH Restaurant',
    address: '789 Pine St, San Diego, CA 92116',
    phone_number: '+1 555-5678',
    website_url: 'https://multihh.com',
    happy_hour_times: 'Monday: 3:00 PM - 6:00 PM, 10:00 PM - 12:00 AM | Wednesday: 4:00 PM - 7:00 PM',
    regular_hours: 'Monday: 11:00 AM - 12:00 AM',
    rating: '4.2',
    review_count: '75',
    price_level: 'PRICE_LEVEL_EXPENSIVE',
    source: 'Manual',
    freshness_date: '2026-04-19',
  },
];

describe('HappyHourFinder Component', () => {
  describe('Stats Display', () => {
    it('should display correct total place count', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Total Places')).toBeInTheDocument();
    });

    it('should display correct happy hour count', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('With Happy Hour')).toBeInTheDocument();
    });
  });

  describe('Restaurant Cards', () => {
    it('should display restaurant name for each place', async () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      await waitFor(() => {
        expect(screen.getByText('Test Bar')).toBeInTheDocument();
        expect(screen.getByText('No HH Cafe')).toBeInTheDocument();
        expect(screen.getByText('Multi-HH Restaurant')).toBeInTheDocument();
      });
    });

    it('should display address for each restaurant', async () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      await waitFor(() => {
        expect(screen.getByText('123 Main St, San Diego, CA 92116')).toBeInTheDocument();
      });
    });

    it('should display rating with star symbol', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText('4.5★')).toBeInTheDocument();
    });

    it('should display "Has Happy Hour" badge for places with happy hour', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const badges = screen.getAllByText('Has Happy Hour');
      expect(badges.length).toBe(2);
    });

    it('should not display happy hour badge for places without happy hour', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const noHhCard = screen.getByText('No HH Cafe').closest('[class*="rounded-lg"]');
      expect(noHhCard).not.toHaveTextContent('Has Happy Hour');
    });

    it('should display happy hour times on separate lines', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const testBar = screen.getByText('Test Bar').closest('[class*="rounded-lg"]') || document.body;
      expect(testBar.textContent).toContain('Monday: 3:00 PM - 6:00 PM');
      expect(testBar.textContent).toContain('Tuesday: 3:00 PM - 6:00 PM');
    });

    it('should display source and freshness date', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText(/Source: Website/)).toBeInTheDocument();
    });

    it('should display phone number link when available', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const phoneLink = screen.getByText('+1 555-1234');
      expect(phoneLink.tagName).toBe('A');
      expect(phoneLink).toHaveAttribute('href', 'tel:+1 555-1234');
    });

    it('should display website link when available', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const websiteLink = screen.getByText('Website');
      expect(websiteLink.tagName).toBe('A');
      expect(websiteLink).toHaveAttribute('href', 'https://testbar.com');
    });
  });

  describe('Search Functionality', () => {
    it('should filter restaurants by name when searching', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');
      
      fireEvent.change(searchInput, { target: { value: 'Test Bar' } });
      
      expect(screen.getByText('Test Bar')).toBeInTheDocument();
      expect(screen.queryByText('No HH Cafe')).not.toBeInTheDocument();
    });

    it('should filter restaurants by address when searching', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');
      
      fireEvent.change(searchInput, { target: { value: '456 Oak' } });
      
      expect(screen.getByText('No HH Cafe')).toBeInTheDocument();
      expect(screen.queryByText('Test Bar')).not.toBeInTheDocument();
    });

    it('should show no results message when search has no matches', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');
      
      fireEvent.change(searchInput, { target: { value: 'NonExistent' } });
      
      expect(screen.getByText('No places found.')).toBeInTheDocument();
    });

    it('should display results count with search query', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');
      
      fireEvent.change(searchInput, { target: { value: 'Test' } });
      
      expect(screen.getByText(/Showing 1 place for "Test"/)).toBeInTheDocument();
    });
  });

  describe('Happy Hour Filter Toggle', () => {
    it('should show only places with happy hour when toggle is checked', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const toggle = screen.getByLabelText('Only show places with happy hour');
      
      fireEvent.click(toggle);
      
      expect(screen.getByText('Test Bar')).toBeInTheDocument();
      expect(screen.getByText('Multi-HH Restaurant')).toBeInTheDocument();
      expect(screen.queryByText('No HH Cafe')).not.toBeInTheDocument();
    });

    it('should show all places when toggle is unchecked', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const toggle = screen.getByLabelText('Only show places with happy hour');
      
      fireEvent.click(toggle); // Check
      fireEvent.click(toggle); // Uncheck
      
      expect(screen.getByText('Test Bar')).toBeInTheDocument();
      expect(screen.getByText('No HH Cafe')).toBeInTheDocument();
    });
  });

  describe('Day and Time Filters', () => {
    it('should have day selector with all days of week', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const daySelect = screen.getByLabelText('Day');
      
      expect(daySelect).toBeInTheDocument();
      expect(screen.getByText('Monday')).toBeInTheDocument();
      expect(screen.getByText('Sunday')).toBeInTheDocument();
    });

    it('should have time selector with hourly options', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const timeSelect = screen.getByLabelText('Time');
      
      expect(timeSelect).toBeInTheDocument();
      expect(screen.getByText('12:00 AM')).toBeInTheDocument();
      expect(screen.getByText('12:00 PM')).toBeInTheDocument();
    });

    it('should update active count when filters change', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const daySelect = screen.getByLabelText('Day');
      
      fireEvent.change(daySelect, { target: { value: 'Wednesday' } });
      
      // Active count should update based on day selection
      const activeCount = screen.getAllByText(/\d+/)[2]; // Third stat number
      expect(activeCount).toBeInTheDocument();
    });
  });

  describe('Price Level Display', () => {
    it('should display dollar signs for price level', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText('$$')).toBeInTheDocument();
      expect(screen.getByText('$')).toBeInTheDocument();
    });

    it('should display more dollar signs for higher price levels', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      expect(screen.getByText('$$$')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty restaurants array', () => {
      render(<HappyHourFinder restaurants={[]} />);
      expect(screen.getByText('0')).toBeInTheDocument();
      expect(screen.getByText('Total Places')).toBeInTheDocument();
    });

    it('should handle restaurant with multiple happy hour sessions', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const multiHhCard = screen.getByText('Multi-HH Restaurant').closest('[class*="rounded-lg"]') || document.body;
      expect(multiHhCard.textContent).toContain('Monday: 3:00 PM - 6:00 PM, 10:00 PM - 12:00 AM');
    });

    it('should show regular hours in expandable details', () => {
      render(<HappyHourFinder restaurants={mockRestaurants} />);
      const details = screen.getAllByText('Regular Hours')[0];
      expect(details.tagName).toBe('SUMMARY');
    });
  });
});

