import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const FIXED_DATE = new Date('2026-04-20T17:00:00'); // Monday 5 PM

// Track all leaflet interactions for assertions
const mockLayers: any[] = [];
const mockMarkers: any[] = [];
let mockMapZoom = 13;
let eventHandlers: Map<string, Set<Function>> = new Map();

function clearMockState() {
  mockLayers.length = 0;
  mockMarkers.length = 0;
  mockMapZoom = 13;
  eventHandlers = new Map();
}

function getHandlers(event: string): Set<Function> {
  if (!eventHandlers.has(event)) eventHandlers.set(event, new Set());
  return eventHandlers.get(event)!;
}

function triggerEvent(event: string) {
  getHandlers(event).forEach((fn) => fn());
}

// Build the mock L object that dynamic import will receive
function createMockL() {
  const mockL = {
    map: vi.fn((container: any) => {
      const mapInstance = {
        setView: vi.fn(() => mapInstance),
        getZoom: vi.fn(() => mockMapZoom),
        setZoom: vi.fn((z: number) => { mockMapZoom = z; }),
        fitBounds: vi.fn(),
        invalidateSize: vi.fn(),
        remove: vi.fn(),
        project: vi.fn((latLng: [number, number], zoom: number) => {
          return { x: latLng[1] * 1000 * zoom, y: latLng[0] * 1000 * zoom };
        }),
        on: vi.fn((event: string, fn: Function) => {
          getHandlers(event).add(fn);
        }),
        addLayer: vi.fn((layer: any) => {
          mockLayers.push(layer);
        }),
        removeLayer: vi.fn((layer: any) => {
          const idx = mockLayers.indexOf(layer);
          if (idx > -1) mockLayers.splice(idx, 1);
        }),
      };
      if (container) {
        (container as any)._leaflet_id = 1;
      }
      return mapInstance;
    }),
    tileLayer: vi.fn(() => ({
      addTo: vi.fn(),
    })),
    layerGroup: vi.fn(() => {
      const group = {
        addTo: vi.fn((map: any) => {
          map.addLayer(group);
          return group;
        }),
        clearLayers: vi.fn(() => {
          mockMarkers.length = 0;
        }),
        addLayer: vi.fn((marker: any) => {
          mockMarkers.push(marker);
        }),
      };
      return group;
    }),
    marker: vi.fn((latLng: [number, number], options: any) => {
      const marker = {
        latLng,
        options,
        popupHtml: null as string | null,
        clickHandler: null as Function | null,
        bindPopup: vi.fn((html: string) => {
          marker.popupHtml = html;
          return marker;
        }),
        on: vi.fn((event: string, fn: Function) => {
          if (event === 'click') marker.clickHandler = fn;
        }),
        addTo: vi.fn((map: any) => {
          map.addLayer(marker);
          return marker;
        }),
      };
      return marker;
    }),
    divIcon: vi.fn((options: any) => options),
  };
  return mockL;
}

// Mock leaflet before any imports — attach to both default and namespace
vi.mock('leaflet', async () => {
  const mockL = createMockL();
  return {
    __esModule: true,
    default: mockL,
    ...mockL,
  };
});

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
    vi.clearAllMocks();
  });

  it('updates marker statuses when time selector changes', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Afternoon Bar',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    // At 5 PM, happy hour is active
    const activeMarker = mockMarkers.find((m) =>
      m.popupHtml?.includes('Active now')
    );
    expect(activeMarker).toBeTruthy();

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
    vi.clearAllMocks();
  });

  it('skips restaurants without latitude or longitude', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Has Location',
        latitude: '32.7157',
        longitude: '-117.1611',
      }),
      createRestaurant({
        restaurant_name: 'No Location',
        latitude: '',
        longitude: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    expect(mockMarkers.length).toBe(1);
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
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    expect(mockMarkers.length).toBe(0);
  });
});

describe('RestaurantMap - User location', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    clearMockState();

    // jsdom has isSecureContext false by default, which blocks geolocation
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
    vi.clearAllMocks();
  });

  it('shows user location marker when location is active', async () => {
    render(<HappyHourFinder restaurants={[createRestaurant()]} />);

    // Open map first so it's initialized when geolocation resolves
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
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

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
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
    vi.clearAllMocks();
  });

  it('switches to list tab when "View details" is clicked', async () => {
    const restaurants = [
      createRestaurant({
        restaurant_name: 'Popup Bar',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
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
    vi.clearAllMocks();
  });

  it('does not crash with zero restaurants', async () => {
    render(<HappyHourFinder restaurants={[]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    expect(mockMarkers.length).toBe(0);
  });

  it('does not crash when all restaurants lack coordinates', async () => {
    const restaurants = [
      createRestaurant({ latitude: '', longitude: '' }),
      createRestaurant({ latitude: '', longitude: '' }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    fireEvent.click(screen.getByRole('button', { name: 'Map' }));

    await waitFor(() => {
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });

    expect(mockMarkers.length).toBe(0);
  });
});
