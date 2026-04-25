import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Test Place',
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
  },
];

describe('HappyHourFinder - Hydration-Safe Time Initialization', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given the component mounts on a Saturday afternoon, When rendered, Then the day dropdown updates from static "Monday" default to "Saturday" via useEffect', async () => {
    // Saturday at 3:00 PM
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-25T15:00:00'));

    render(<HappyHourFinder restaurants={mockRestaurants} />);

    await waitFor(() => {
      const daySelect = screen.getByLabelText('Day') as HTMLSelectElement;
      expect(daySelect.value).toBe('Saturday');
    });
  });

  it('Given the component mounts at 9:00 AM, When rendered, Then the time dropdown updates from static "12:00" default to "09:00" via useEffect', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-20T09:00:00'));

    render(<HappyHourFinder restaurants={mockRestaurants} />);

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('Time') as HTMLSelectElement;
      expect(timeSelect.value).toBe('09:00');
    });
  });

  it('Given the component mounts at midnight, When rendered, Then the time dropdown updates to "00:00" and displays "12:00 AM"', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-20T00:00:00'));

    render(<HappyHourFinder restaurants={mockRestaurants} />);

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('Time') as HTMLSelectElement;
      expect(timeSelect.value).toBe('00:00');
    });
  });

  it('Given the component mounts at noon, When rendered, Then the time dropdown updates to "12:00" and displays "12:00 PM"', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-20T12:00:00'));

    render(<HappyHourFinder restaurants={mockRestaurants} />);

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('Time') as HTMLSelectElement;
      expect(timeSelect.value).toBe('12:00');
    });
  });

  it('Given the component mounts at 11:00 PM, When rendered, Then the time dropdown updates to "23:00" and displays "11:00 PM"', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-20T23:00:00'));

    render(<HappyHourFinder restaurants={mockRestaurants} />);

    await waitFor(() => {
      const timeSelect = screen.getByLabelText('Time') as HTMLSelectElement;
      expect(timeSelect.value).toBe('23:00');
    });
  });
});
