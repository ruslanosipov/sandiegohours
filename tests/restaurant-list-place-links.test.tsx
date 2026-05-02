import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import RestaurantList from '../src/app/components/RestaurantList';
import { HappyHourPlace } from '../src/types/happy-hour';

// Mock date to Saturday at 4:00 PM
const MOCK_DATE = new Date('2026-01-10T16:00:00');

describe('RestaurantList - Place Page Links', () => {
  const restaurants: HappyHourPlace[] = [
    {
      restaurant_name: 'Linked Bar',
      address: '123 Main St, San Diego, CA 92104',
      phone_number: '(619) 555-1234',
      website_url: 'https://example.com',
      happy_hour_times: 'Saturday: 3:00 PM - 6:00 PM',
      regular_hours: 'Monday: 10:00 AM - 10:00 PM',
      rating: '4.5',
      review_count: '100',
      price_level: 'PRICE_LEVEL_MODERATE',
      source: 'Google Places API (Happy Hours)',
      freshness_date: '2026-01-01',
      place_id: 'ChIJlinked123',
      google_maps_url: 'https://maps.example.com/linked',
    },
    {
      restaurant_name: 'No Link Bar',
      address: '456 Oak St, San Diego, CA 92104',
      phone_number: '',
      website_url: '',
      happy_hour_times: '',
      regular_hours: '',
      rating: '',
      review_count: '',
      price_level: '',
      source: 'Google Places API',
      freshness_date: '2026-01-01',
      // no place_id
    },
  ];

  it('renders restaurant name as link when place_id exists', () => {
    render(
      <RestaurantList
        restaurants={restaurants}
        selectedDateTime={MOCK_DATE}
        selectedDay="Saturday"
      />
    );

    const link = screen.getByRole('link', { name: 'Linked Bar' });
    expect(link).toHaveAttribute('href', '/places/ChIJlinked123');
  });

  it('renders plain heading when place_id is missing', () => {
    render(
      <RestaurantList
        restaurants={restaurants}
        selectedDateTime={MOCK_DATE}
        selectedDay="Saturday"
      />
    );

    const heading = screen.getByRole('heading', { name: 'No Link Bar' });
    expect(heading.tagName).toBe('H3');
    // Ensure it's not inside a link
    expect(heading.closest('a')).toBeNull();
  });

  it('renders all restaurants regardless of place_id presence', () => {
    render(
      <RestaurantList
        restaurants={restaurants}
        selectedDateTime={MOCK_DATE}
        selectedDay="Saturday"
      />
    );

    expect(screen.getByText('Linked Bar')).toBeInTheDocument();
    expect(screen.getByText('No Link Bar')).toBeInTheDocument();
  });
});
