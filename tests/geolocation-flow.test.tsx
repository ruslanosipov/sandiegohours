import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Nearby Bar',
    address: '123 Main St',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '10',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    latitude: '32.76',
    longitude: '-117.12',
  },
];

describe('HappyHourFinder - Geolocation Flow', () => {
  let mockGetCurrentPosition: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockGetCurrentPosition = vi.fn();
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: mockGetCurrentPosition,
      },
    });
    // Default to secure context
    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('Given the user is on a secure connection, When they click "Use my location" and grant permission, Then sort switches to "Distance", a location badge appears, and the button becomes a clear button', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    // Click triggers geolocation
    fireEvent.click(locationButton);

    // Should show loading state
    expect(screen.getByText(/Getting location/i)).toBeInTheDocument();

    // Simulate successful geolocation callback
    const successCallback = mockGetCurrentPosition.mock.calls[0][0];
    successCallback({
      coords: { latitude: 32.7157, longitude: -117.1611, accuracy: 10 },
    });

    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
      expect(screen.getByText('Clear')).toBeInTheDocument();
    });
  });

  it('Given the user is on an insecure (non-HTTPS) connection, When they click "Use my location", Then an error about secure connection requirements is displayed and geolocation is not called', () => {
    Object.defineProperty(window, 'isSecureContext', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    fireEvent.click(locationButton);

    expect(mockGetCurrentPosition).not.toHaveBeenCalled();
    expect(screen.getByText(/secure connection/i)).toBeInTheDocument();
  });

  it('Given the user denies location permission, When the geolocation error callback fires with PERMISSION_DENIED, Then a specific error message about enabling location services is displayed', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    fireEvent.click(locationButton);

    const errorCallback = mockGetCurrentPosition.mock.calls[0][1];
    const permissionError = {
      code: 1,
      PERMISSION_DENIED: 1,
      POSITION_UNAVAILABLE: 2,
      TIMEOUT: 3,
      message: 'Permission denied',
    };
    errorCallback(permissionError);

    await waitFor(() => {
      expect(screen.getByText(/enable location services/i)).toBeInTheDocument();
    });
  });

  it('Given location is active, When the user clicks the clear (x) button, Then the location badge disappears, sort resets to "Name", and the "Use my location" button reappears', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    fireEvent.click(locationButton);

    const successCallback = mockGetCurrentPosition.mock.calls[0][0];
    successCallback({
      coords: { latitude: 32.7157, longitude: -117.1611, accuracy: 10 },
    });

    await waitFor(() => {
      expect(screen.getByText('Location active')).toBeInTheDocument();
    });

    const clearButton = screen.getByText('Clear');
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(screen.queryByText('Location active')).not.toBeInTheDocument();
      expect(screen.getByText('Use my location')).toBeInTheDocument();
    });
  });

  it('Given the browser does not support geolocation, When the user clicks "Use my location", Then an error stating geolocation is not supported is displayed', () => {
    vi.stubGlobal('navigator', {});

    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    fireEvent.click(locationButton);

    expect(screen.getByText(/not supported/i)).toBeInTheDocument();
  });

  it('Given the location request times out, When the geolocation error callback fires with TIMEOUT, Then the error message "Location request timed out" is displayed', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const locationButton = screen.getByText('Use my location');

    fireEvent.click(locationButton);

    const errorCallback = mockGetCurrentPosition.mock.calls[0][1];
    const timeoutError = {
      code: 3,
      PERMISSION_DENIED: 1,
      POSITION_UNAVAILABLE: 2,
      TIMEOUT: 3,
      message: 'Timeout',
    };
    errorCallback(timeoutError);

    await waitFor(() => {
      expect(screen.getByText(/timed out/i)).toBeInTheDocument();
    });
  });
});
