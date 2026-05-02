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
    neighborhood: 'north_park',
    ...overrides,
  };
}

describe('HappyHourFinder - URL Sync Reading', () => {
  let replaceStateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    replaceStateSpy = vi.fn();
    vi.stubGlobal('history', { ...window.history, replaceState: replaceStateSpy });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function setSearch(search: string) {
    const url = new URL('http://localhost:3000/');
    url.search = search;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: url.toString(),
        search: url.search,
        pathname: url.pathname,
      },
    });
  }

  it('reads ?tab=list from URL and activates list tab', async () => {
    setSearch('?tab=list');
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Alpha' })]} />);
    await waitFor(() => {
      expect(screen.getByTestId('list-view')).not.toHaveClass('hidden');
      expect(screen.getByTestId('map-view')).toHaveClass('hidden');
    });
  });

  it('reads ?tab=map from URL and keeps map tab active (default)', async () => {
    setSearch('?tab=map');
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Alpha' })]} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).not.toHaveClass('hidden');
    });
  });

  it('reads ?neighborhood=north_park from URL and filters to North Park', async () => {
    setSearch('?neighborhood=north_park');
    const restaurants = [
      createRestaurant({ restaurant_name: 'NP Bar', neighborhood: 'north_park' }),
      createRestaurant({ restaurant_name: 'SP Bar', neighborhood: 'south_park' }),
    ];
    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByText('NP Bar')).toBeInTheDocument();
      expect(screen.queryByText('SP Bar')).not.toBeInTheDocument();
    });
  });

  it('reads ?search=sushi from URL and populates search input', async () => {
    setSearch('?search=sushi');
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Sushi Place' })]} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue('sushi')).toBeInTheDocument();
      expect(screen.getByText('Sushi Place')).toBeInTheDocument();
    });
  });

  it('reads ?day=Saturday from URL and sets day dropdown', async () => {
    setSearch('?day=Saturday');
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    await waitFor(() => {
      const daySelect = screen.getByLabelText('Day') as HTMLSelectElement;
      expect(daySelect.value).toBe('Saturday');
    });
  });

  it('reads ?time=21:00 from URL and sets time dropdown', async () => {
    setSearch('?time=21:00');
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    await waitFor(() => {
      const timeSelect = screen.getByLabelText('Time') as HTMLSelectElement;
      expect(timeSelect.value).toBe('21:00');
    });
  });

  it('reads ?hh_has=false from URL and unchecks "Has happy hour"', async () => {
    setSearch('?hh_has=false');
    render(<HappyHourFinder restaurants={[createRestaurant({ happy_hour_times: 'Monday: 3:00 PM - 6:00 PM' })]} />);
    await waitFor(() => {
      const checkbox = screen.getByLabelText('Has happy hour') as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
    });
  });

  it('reads ?hh_now=true from URL and checks "Happy hour now"', async () => {
    // At 17:00 on Monday, a place with hh 4PM-6PM should show as active
    setSearch('?hh_now=true');
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Active HH',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
      createRestaurant({
        restaurant_name: 'Inactive HH',
        happy_hour_times: 'Monday: 11:00 AM - 2:00 PM',
      }),
    ];
    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByText('Active HH')).toBeInTheDocument();
      expect(screen.queryByText('Inactive HH')).not.toBeInTheDocument();
    });
  });

  it('ignores unknown URL params gracefully', async () => {
    setSearch('?tab=evil&neighborhood=nonexistent&foo=bar');
    render(<HappyHourFinder restaurants={[createRestaurant({ restaurant_name: 'Zed' })]} />);
    await waitFor(() => {
      expect(screen.getByText('Zed')).toBeInTheDocument();
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });
  });
});

describe('HappyHourFinder - URL Sync Writing', () => {
  let replaceStateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    replaceStateSpy = vi.fn();
    vi.stubGlobal('history', { ...window.history, replaceState: replaceStateSpy });
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: 'http://localhost:3000/', search: '', pathname: '/' },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('updates URL to ?tab=list when List tab is clicked', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    fireEvent.click(screen.getByRole('button', { name: 'List' }));
    await waitFor(() => {
      expect(replaceStateSpy).toHaveBeenCalledWith(
        expect.anything(),
        '',
        expect.stringContaining('tab=list')
      );
    });
  });

  it('removes ?tab from URL when Map tab is clicked (map is default)', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    fireEvent.click(screen.getByRole('button', { name: 'List' }));
    await waitFor(() => expect(replaceStateSpy).toHaveBeenCalled());
    replaceStateSpy.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    await waitFor(() => {
      const lastCall = replaceStateSpy.mock.calls[replaceStateSpy.mock.calls.length - 1];
      expect(lastCall?.[2]).not.toContain('tab=');
    });
  });

  it('updates URL to ?neighborhood=north_park when neighborhood badge is selected', async () => {
    const restaurants = [
      createRestaurant({ restaurant_name: 'NP', neighborhood: 'north_park' }),
      createRestaurant({ restaurant_name: 'SP', neighborhood: 'south_park' }),
    ];
    render(<HappyHourFinder restaurants={restaurants} />);
    // Find and click the North Park badge (aria label NeighborhoodBadgeBar)
    const npBadge = screen.getByText('North Park');
    fireEvent.click(npBadge);
    await waitFor(() => {
      expect(replaceStateSpy).toHaveBeenCalledWith(
        expect.anything(),
        '',
        expect.stringContaining('neighborhood=north_park')
      );
    });
  });

  it('updates URL to ?search=burger when search input changes', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);
    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');
    fireEvent.change(searchInput, { target: { value: 'burger' } });
    await waitFor(() => {
      expect(replaceStateSpy).toHaveBeenCalledWith(
        expect.anything(),
        '',
        expect.stringContaining('search=burger')
      );
    });
  });
});
