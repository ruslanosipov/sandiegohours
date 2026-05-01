import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';
import {
  mockLayers,
  mockMarkers,
  clearMockState,
  triggerEvent,
} from './__mocks__/leaflet';

const FIXED_DATE = new Date('2026-04-20T17:00:00'); // Monday 5 PM

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

describe('RestaurantMap - Time selector regression', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('updates marker statuses when time selector changes', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Afternoon Bar',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    await waitFor(() => {
      const activeMarker = mockMarkers.find((m) =>
        m.popupHtml?.includes('Active now')
      );
      expect(activeMarker).toBeTruthy();
    });

    // Change time to 8 PM (after happy hour)
    const timeSelect = screen.getByLabelText('Time');
    fireEvent.change(timeSelect, { target: { value: '20:00' } });

    await waitFor(() => {
      const inactiveMarker = mockMarkers.find((m) =>
        m.popupHtml?.includes('Not active now')
      );
      expect(inactiveMarker).toBeTruthy();
    });

    // Also verify zoomend uses updated time (regression test for stale closure)
    triggerEvent('zoomend');

    await waitFor(() => {
      const zoomedMarker = mockMarkers.find((m) =>
        m.popupHtml?.includes('Not active now')
      );
      expect(zoomedMarker).toBeTruthy();
    });
  });
});

describe('RestaurantMap - Missing coordinates', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('skips restaurants without latitude or longitude', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Has Location',
        latitude: '32.7157',
        longitude: '-117.1611',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
      createRestaurant({
        restaurant_name: 'No Location',
        latitude: '',
        longitude: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockMarkers.length).toBe(1);
    }, { timeout: 3000 });
    expect(mockMarkers[0].popupHtml).toContain('Has Location');
  });

  it('handles partially missing coordinates (only lat)', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Partial Location',
        latitude: '32.7157',
        longitude: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockMarkers.length).toBe(0);
    });
  });
});

describe('RestaurantMap - User location', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();

    vi.stubGlobal('isSecureContext', true);
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn((success) => {
          success({
            coords: { latitude: 32.7600, longitude: -117.1200, accuracy: 10 },
          });
        }),
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('shows user location marker when location is active', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Use my location'));

    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
    });

    const userMarker = mockLayers.find(
      (m) => m.options?.icon?.className === 'custom-marker user-location'
    );
    expect(userMarker).toBeTruthy();
    expect(userMarker.latLng).toEqual([32.76, -117.12]);
  });

  it('removes user location marker when location is cleared', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);

    fireEvent.click(screen.getByText('Use my location'));
    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Clear'));

    await waitFor(() => {
      expect(screen.queryByText('Location active')).not.toBeInTheDocument();
    });

    const userMarker = mockMarkers.find(
      (m) => m.options?.className === 'custom-marker user-location'
    );
    expect(userMarker).toBeFalsy();
  });
});

describe('RestaurantMap - Popup interactions', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('switches to list tab when "View details" is clicked', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Popup Bar',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    const mapContainer = screen.getByTestId('restaurant-map');
    const link = document.createElement('div');
    link.className = 'popup-link';
    link.setAttribute('data-index', '0');
    mapContainer.appendChild(link);

    fireEvent.click(link);

    await waitFor(() => {
      expect(screen.getByTestId('list-view')).not.toHaveClass('hidden');
    });
  });
});

describe('RestaurantMap - Edge cases', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not crash with zero restaurants', async () => {
    render(<HappyHourFinder restaurants={[]} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockMarkers.length).toBe(0);
    });
  });

  it('does not crash when all restaurants lack coordinates', async () => {
    const restaurants = [
      createRestaurant({ latitude: '', longitude: '' }),
      createRestaurant({ latitude: '', longitude: '' }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockMarkers.length).toBe(0);
    });
  });
});
