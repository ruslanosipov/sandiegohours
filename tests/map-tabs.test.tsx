import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const FIXED_DATE = new Date('2026-04-20T17:00:00'); // Monday

function createRestaurant(overrides: Partial<HappyHourPlace> = {}): HappyHourPlace {
  return {
    restaurant_name: 'Test Restaurant',
    address: '123 Main St, San Diego, CA 92116',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '100',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    latitude: '32.7157',
    longitude: '-117.1611',
    ...overrides,
  };
}

describe('HappyHourFinder - Tabs', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders List and Map tabs', () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    expect(screen.getByRole('button', { name: 'List' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Map' })).toBeInTheDocument();
  });

  it('defaults to List tab being active', () => {
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Alpha' })]} />);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
  });

  it('switches to Map tab when clicked', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    const mapButton = screen.getByRole('button', { name: 'Map' });
    fireEvent.click(mapButton);

    await waitFor(() => {
      // Map view container should be visible
      expect(screen.getByTestId('map-view')).not.toHaveClass('hidden');
      expect(screen.getByTestId('restaurant-map')).toBeInTheDocument();
    });
  });

  it('hides list and shows map when Map tab is active', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Hidden In Map' })]} />);
    expect(screen.getByTestId('list-view')).not.toHaveClass('hidden');
    expect(screen.queryByTestId('map-view')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('list-view')).toHaveClass('hidden');
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });
  });

  it('returns to List tab when List button is clicked after Map', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Back To List' })]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).not.toHaveClass('hidden');
    });

    fireEvent.click(screen.getByRole('button', { name: 'List' }));

    await waitFor(() => {
      expect(screen.getByTestId('list-view')).not.toHaveClass('hidden');
      expect(screen.getByText('Back To List')).toBeInTheDocument();
    });
  });

  it('applies filters to map view as well as list view', async () => {
    const restaurants = [
      createRestaurant({ restaurant_name: 'Has HH', happy_hour_times: 'Monday: 4:00 PM - 6:00 PM' }),
      createRestaurant({ restaurant_name: 'No HH', happy_hour_times: '' }),
    ];
    render(<HappyHourFinder restaurants={restaurants} />);

    const checkbox = screen.getByLabelText('Only show places with happy hour');
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(screen.queryByText('No HH')).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    // Switch back to list to verify filter still holds
    fireEvent.click(screen.getByRole('button', { name: 'List' }));
    await waitFor(() => {
      expect(screen.queryByText('No HH')).not.toBeInTheDocument();
    });
  });
});
