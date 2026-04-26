import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const FIXED_DATE = new Date('2026-04-20T17:00:00');

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Nearby Bar',
    address: '100 Main St',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '10',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    latitude: '32.760',
    longitude: '-117.120',
  },
  {
    restaurant_name: 'Faraway Pub',
    address: '900 Oak St',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '10',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    latitude: '32.720',
    longitude: '-117.160',
  },
];

describe('HappyHourFinder - Sorting by Distance', () => {
  let mockGetCurrentPosition: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    mockGetCurrentPosition = vi.fn();
    vi.stubGlobal('navigator', {
      geolocation: { getCurrentPosition: mockGetCurrentPosition },
    });
    Object.defineProperty(window, 'isSecureContext', {
      value: true, writable: true, configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('Given the user has not shared their location, When they open the "Sort by" dropdown, Then the "Distance" option is disabled', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const distanceOption = screen.getByText('Distance');
    expect(distanceOption).toBeDisabled();
  });

  it('Given the user has shared their location, When they select "Distance", Then restaurants are sorted from closest to farthest', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);

    // Trigger geolocation
    fireEvent.click(screen.getByText('Use my location'));
    const successCallback = mockGetCurrentPosition.mock.calls[0][0];
    successCallback({
      coords: { latitude: 32.761, longitude: -117.121, accuracy: 10 },
    });

    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
    });

    // Select Distance sort
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'distance' } });

    // Nearby Bar should appear before Faraway Pub
    const headings = screen.getAllByRole('heading');
    const names = headings.map(h => h.textContent);
    const nearbyIndex = names.indexOf('Nearby Bar');
    const farawayIndex = names.indexOf('Faraway Pub');
    expect(nearbyIndex).toBeLessThan(farawayIndex);
  });

  it('Given location is active and sorting by distance, When the user clears location, Then sort reverts to "Name"', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);

    fireEvent.click(screen.getByText('Use my location'));
    const successCallback = mockGetCurrentPosition.mock.calls[0][0];
    successCallback({
      coords: { latitude: 32.761, longitude: -117.121, accuracy: 10 },
    });

    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'distance' } });

    // Clear location
    fireEvent.click(screen.getByText('Clear'));

    await waitFor(() => {
      expect(screen.getByText('Use my location')).toBeInTheDocument();
      expect(screen.getByLabelText('Sort by')).toHaveValue('name');
    });
  });
});
