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
    menu_summary: '$5 appetizers and $4 beers',
    cheapest_drink: '$4 Sapporo',
    cheapest_food: '$5 Gyoza',
  },
];

function switchToList() {
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
}

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

  it('defaults to showing only happy-hour restaurants and map view', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    expect(screen.getByTestId('map-view')).not.toHaveClass('hidden');
    expect(screen.getByTestId('list-view')).toHaveClass('hidden');
    expect(screen.getByLabelText('Has happy hour')).toBeChecked();
    expect(screen.getByLabelText('Happy hour now')).not.toBeChecked();
  });

  it('renders happy-hour restaurants by default (Has happy hour checked)', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    expect(screen.getByText('The Rabbit Hole')).toBeInTheDocument();
    expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();
    expect(screen.queryByText("Rudford's Restaurant")).not.toBeInTheDocument();
  });

  it('shows correct stats counts', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const statsText = document.body.textContent || '';
    expect(statsText).toContain('2 with Happy Hour');
    expect(statsText).toContain('2 Active Now');
    expect(statsText).toContain('Showing 2 places');
  });

  it('filters by search query', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');

    fireEvent.change(searchInput, { target: { value: 'Ramen' } });

    await waitFor(() => {
      expect(screen.queryByText('The Rabbit Hole')).not.toBeInTheDocument();
      expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();
    });
  });

  it('filters by address search query', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');

    fireEvent.change(searchInput, { target: { value: 'El Cajon' } });

    await waitFor(() => {
      // Rudford's has no HH so hidden even though address matches
      expect(screen.queryByText('The Rabbit Hole')).not.toBeInTheDocument();
      expect(screen.queryByText("Rudford's Restaurant")).not.toBeInTheDocument();
      expect(screen.getByText('No places found.')).toBeInTheDocument();
    });

    // Uncheck Has happy hour to show Rudford's via address search
    fireEvent.click(screen.getByLabelText('Has happy hour'));
    await waitFor(() => {
      expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();
    });
  });

  it('toggles "Has happy hour" checkbox on and off', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    const checkbox = screen.getByLabelText('Has happy hour');

    // Rudford's has no HH so hidden by default
    expect(screen.getByText('The Rabbit Hole')).toBeInTheDocument();
    expect(screen.queryByText("Rudford's Restaurant")).not.toBeInTheDocument();

    fireEvent.click(checkbox); // uncheck

    await waitFor(() => {
      expect(screen.getByText("Rudford's Restaurant")).toBeInTheDocument();
    });

    fireEvent.click(checkbox); // check again

    await waitFor(() => {
      expect(screen.queryByText("Rudford's Restaurant")).not.toBeInTheDocument();
    });
  });

  it('toggles "Happy hour now" checkbox', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
    const nowCheckbox = screen.getByLabelText('Happy hour now');

    // Monday at 5 PM: both Rabbit Hole (4-6 PM) and Nozaru (4-6 PM) are active
    expect(screen.getByText('The Rabbit Hole')).toBeInTheDocument();
    expect(screen.getByText('Nozaru Ramen Bar')).toBeInTheDocument();

    // Change time to 8 PM – neither is active
    fireEvent.change(screen.getByLabelText('Time'), { target: { value: '20:00' } });
    fireEvent.click(nowCheckbox);

    await waitFor(() => {
      expect(screen.queryByText('The Rabbit Hole')).not.toBeInTheDocument();
      expect(screen.queryByText('Nozaru Ramen Bar')).not.toBeInTheDocument();
    });
  });

  it('expands and collapses happy hour details via accordion button', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();
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
    switchToList();
    expect(screen.getByText('Happy Hour Deals')).toBeInTheDocument();
    expect(screen.getByText('$5 appetizers and $4 beers')).toBeInTheDocument();
  });

  it('renders "Use my location" button with pin icon', () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    const button = screen.getByText('Use my location');
    expect(button).toBeInTheDocument();
    const svg = button.querySelector('svg');
    expect(svg).not.toBeNull();
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
