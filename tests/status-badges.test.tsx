import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

// Fixed date: Monday at 5:00 PM (17:00) for deterministic happy hour testing
const FIXED_DATE = new Date('2026-04-20T17:00:00'); // Monday, 5 PM

function createRestaurant(overrides: Partial<HappyHourPlace>): HappyHourPlace {
  return {
    restaurant_name: 'Test Restaurant',
    address: '123 Test St',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '100',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
    ...overrides,
  };
}

describe('HappyHourFinder - Status Badges and Visual Indicators', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given a restaurant has an active happy hour for the selected day/time, When the card renders, Then it displays a green "Happy Hour Now!" badge and a yellow ring border around the card', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'Active Bar',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM | Tuesday: 4:00 PM - 6:00 PM',
      }),
    ];

    const { container } = render(<HappyHourFinder restaurants={restaurants} />);

    // Badge text
    expect(screen.getByText('Happy Hour Now!')).toBeInTheDocument();

    // Yellow ring border on card
    const card = container.querySelector('.ring-brand-yellow');
    expect(card).not.toBeNull();
  });

  it('Given a restaurant has no happy hour data at all, When the card renders, Then it displays a red "No Happy Hour" badge', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'No HH Bar',
        happy_hour_times: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    expect(screen.getByText('No Happy Hour')).toBeInTheDocument();

    // Verify it's styled as red
    const badge = screen.getByText('No Happy Hour');
    expect(badge.className).toContain('bg-red-100');
    expect(badge.className).toContain('text-red-700');
  });

  it('Given a restaurant is closed today for happy hour, When the card renders, Then it displays a gray "No Happy Hour Today" badge', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'Closed Today Bar',
        happy_hour_times: 'Saturday: Closed | Sunday: Closed | Monday: Closed | Tuesday: 3:00 PM - 5:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    expect(screen.getByText('No Happy Hour Today')).toBeInTheDocument();
  });

  it('Given a restaurant\'s happy hour will happen later today, When the card renders, Then it displays a blue "Happy Hour Later" badge', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'Later Bar',
        happy_hour_times: 'Monday: 8:00 PM - 10:00 PM | Tuesday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    expect(screen.getByText('Happy Hour Later')).toBeInTheDocument();
  });

  it('Given a restaurant\'s happy hour has already passed today, When the card renders, Then it displays a gray "Happy Hour Passed" badge', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'Passed Bar',
        happy_hour_times: 'Monday: 2:00 PM - 4:00 PM | Tuesday: 4:00 PM - 6:00 PM',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    expect(screen.getByText('Happy Hour Passed')).toBeInTheDocument();
  });

  it('Given multiple restaurants with different statuses, When the cards render, Then each badge reflects its correct status', () => {
    const restaurants: HappyHourPlace[] = [
      createRestaurant({
        restaurant_name: 'Active Now',
        happy_hour_times: 'Monday: 4:00 PM - 6:00 PM',
      }),
      createRestaurant({
        restaurant_name: 'None Today',
        happy_hour_times: 'Tuesday: 3:00 PM - 5:00 PM | Wednesday: 3:00 PM - 5:00 PM',
      }),
      createRestaurant({
        restaurant_name: 'No Data',
        happy_hour_times: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);

    // Verify restaurant names are present (use heading role to disambiguate from stat labels)
    expect(screen.getByRole('heading', { name: 'Active Now' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'None Today' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'No Data' })).toBeInTheDocument();

    // Verify all three badge types appear
    expect(screen.getByText('Happy Hour Now!')).toBeInTheDocument();
    expect(screen.getByText('No Happy Hour Today')).toBeInTheDocument();
    expect(screen.getByText('No Happy Hour')).toBeInTheDocument();
  });
});
