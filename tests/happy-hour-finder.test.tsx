import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

// Fixed date: Monday at 5:00 PM so mock happy hours are active
const FIXED_DATE = new Date('2026-04-20T17:00:00'); // Monday

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'The Rabbit Hole',
    address: '3377 Adams Ave, San Diego, CA 92116',
    phone_number: '(619) 255-4653',
    website_url: 'http://rabbitholesd.com/',
    happy_hour_times: 'Monday: 4:00 PM - 6:00 PM | Tuesday: 4:00 PM - 6:00 PM | Wednesday: 4:00 PM - 6:00 PM | Thursday: 4:00 PM - 6:00 PM | Friday: 4:00 PM - 6:00 PM | Saturday: Closed | Sunday: Closed',
    regular_hours: 'Monday: 12:00 PM - 11:00 PM | Tuesday: 12:00 PM - 11:00 PM | Wednesday: 12:00 PM - 11:00 PM | Thursday: 12:00 PM - 11:00 PM | Friday: 12:00 PM - 1:00 AM | Saturday: 10:00 AM - 1:00 AM | Sunday: 10:00 AM - 11:00 PM',
    rating: '4.3',
    review_count: '1377',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-24',
    latitude: '32.7631057',
    longitude: '-117.1210771',
    google_maps_url: 'https://maps.google.com/?cid=123',
    generative_summary: 'Upscale pub food & craft cocktails.',
  },
  {
    restaurant_name: 'Rudford\'s Restaurant',
    address: '2900 El Cajon Blvd, San Diego, CA 92104',
    phone_number: '(619) 282-8423',
    website_url: 'http://www.rudfords.com/',
    happy_hour_times: '',
    regular_hours: 'Monday: Open 24 hours | Tuesday: Open 24 hours | Wednesday: Open 24 hours | Thursday: Open 24 hours | Friday: Open 24 hours | Saturday: Open 24 hours | Sunday: Open 24 hours',
    rating: '4.4',
    review_count: '4726',
    price_level: 'PRICE_LEVEL_INEXPENSIVE',
    source: 'google_maps_api',
    freshness_date: '2026-04-24',
    latitude: '32.7556258',
    longitude: '-117.1312339',
    google_maps_url: 'https://maps.google.com/?cid=456',
  },
  {
    restaurant_name: 'Nozaru Ramen Bar',
    address: '3375 Adams Ave, San Diego, CA 92116',
    phone_number: '(619) 564-7183',
    website_url: 'http://nozaruramen.com/',
    happy_hour_times: 'Monday: 4:00 PM - 6:00 PM | Tuesday: 4:00 PM - 6:00 PM | Wednesday: 4:00 PM - 6:00 PM | Thursday: 4:00 PM - 6:00 PM | Friday: 4:00 PM - 6:00 PM | Saturday: 4:00 PM - 6:00 PM | Sunday: 4:00 PM - 6:00 PM',
    regular_hours: 'Monday: 4:00 PM - 9:00 PM | Tuesday: 4:00 PM - 9:00 PM | Wednesday: 4:00 PM - 9:00 PM | Thursday: 4:00 PM - 9:00 PM | Friday: 12:00 PM - 10:00 PM | Saturday: 12:00 PM - 10:00 PM | Sunday: 12:00 PM - 9:00 PM',
    rating: '4.5',
    review_count: '373',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'Google Places API (Happy Hours)',
    freshness_date: '2026-04-24',
    latitude: '32.7631174',
    longitude: '-117.1211899',
    google_maps_url: 'https://maps.google.com/?cid=789',
    generative_summary: 'Small Japanese place with ramen and sushi.',
    menu_summary: '$5 appetizers and $4 beers',
    cheapest_drink: '$4 Sapporo',
    cheapest_food: '$5 Gyoza',
  },
];

describe('HappyHourFinder', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn(),
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('renders all restaurants by default', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    expect(screen.getByText('The Rabbit Hole')).toBeInTheDocument();
    expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();
    expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();
  });

  it('shows correct stats counts', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const counts = screen.getAllByText('2');
    expect(counts.length).toBe(2); // With Happy Hour + Active Now
    expect(screen.getByText('3')).toBeInTheDocument(); // Total Places
  });

  it('filters by search query', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');

    fireEvent.change(searchInput, { target: { value: 'Ramen' } });

    await waitFor(() => {
      expect(screen.queryByText('The Rabbit Hole')).not.toBeInTheDocument();
      expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();
    });
  });

  it('filters by address search query', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const searchInput = screen.getByPlaceholderText('Search by restaurant name or address...');

    fireEvent.change(searchInput, { target: { value: 'El Cajon' } });

    await waitFor(() => {
      expect(screen.queryByText('The Rabbit Hole')).not.toBeInTheDocument();
      expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();
    });
  });

  it('toggles "Only show places with happy hour" checkbox', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const checkbox = screen.getByLabelText('Only show places with happy hour');

    expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();

    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(screen.queryByText("Rudford's Restaurant")).not.toBeInTheDocument();
      expect(screen.getByText('The Rabbit Hole')).toBeInTheDocument();
      expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();
    });

    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();
    });
  });

  it('expands and collapses happy hour details via accordion button', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const rabbitHoleButton = screen.getAllByRole('button', { name: /Happy Hour/i })[0];

    // Use a non-Monday day to avoid matching the preview text shown on the collapsed button
    expect(screen.queryByText(/Tuesday: 4:00 PM - 6:00 PM/i)).not.toBeInTheDocument();

    fireEvent.click(rabbitHoleButton);

    await waitFor(() => {
      expect(screen.getByText(/Tuesday: 4:00 PM - 6:00 PM/i)).toBeInTheDocument();
    });

    fireEvent.click(rabbitHoleButton);

    await waitFor(() => {
      expect(screen.queryByText(/Tuesday: 4:00 PM - 6:00 PM/i)).not.toBeInTheDocument();
    });
  });

  it('renders menu summary and cheapest items when available', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    expect(screen.getByText('Happy Hour Deals')).toBeInTheDocument();
    expect(screen.getByText('$5 appetizers and $4 beers')).toBeInTheDocument();
    expect(screen.getByText(/\$4 Sapporo/i)).toBeInTheDocument();
    expect(screen.getByText(/\$5 Gyoza/i)).toBeInTheDocument();
  });

  it('renders "Use my location" button', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    expect(screen.getByText('📍 Use my location')).toBeInTheDocument();
  });

  it('updates selected day and time via dropdowns', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const daySelect = screen.getByLabelText('Day');
    const timeSelect = screen.getByLabelText('Time');

    fireEvent.change(daySelect, { target: { value: 'Friday' } });
    fireEvent.change(timeSelect, { target: { value: '17:00' } });

    await waitFor(() => {
      expect(daySelect).toHaveValue('Friday');
      expect(timeSelect).toHaveValue('17:00');
    });
  });
});
