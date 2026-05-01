import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const FIXED_DATE = new Date('2026-04-20T17:00:00');

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Maps Link Bar',
    address: '123 Main St, San Diego',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '10',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    google_maps_url: 'https://maps.google.com/?cid=123',
  },
  {
    restaurant_name: 'No Maps Bar',
    address: '456 Oak St, San Diego',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '10',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
  },
];

function switchToList() {
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
}

describe('HappyHourFinder - Google Maps Address Links', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a restaurant has a google_maps_url, When the card renders, Then the address is a clickable link opening in a new tab', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    const link = screen.getByText('123 Main St, San Diego').closest('a');
    expect(link).not.toBeNull();
    expect(link).toHaveAttribute('href', 'https://maps.google.com/?cid=123');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('Given a restaurant does not have a google_maps_url, When the card renders, Then the address is plain text without a link', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    const text = screen.getByText('456 Oak St, San Diego');
    expect(text.tagName.toLowerCase()).not.toBe('a');
    expect(text.closest('a')).toBeNull();
  });

  it('Given a restaurant with google_maps_url, When the link renders, Then it contains a map pin SVG icon', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    const link = screen.getByText('123 Main St, San Diego').closest('a');
    const svg = link?.querySelector('svg');
    expect(svg).not.toBeNull();
  });
});
