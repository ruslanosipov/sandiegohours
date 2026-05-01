import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

// Fixed to Monday at 5:00 PM for consistent testing
const FIXED_DATE = new Date('2026-04-20T17:00:00');

const mockRestaurants: HappyHourPlace[] = [
  {
    restaurant_name: 'Sushi Monday',
    address: '111 Adams Ave',
    phone_number: '',
    website_url: '',
    happy_hour_times: 'Monday: 4:00 PM - 6:00 PM | Wednesday: 4:00 PM - 6:00 PM',
    regular_hours: '',
    rating: '4.5',
    review_count: '100',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
  },
  {
    restaurant_name: 'Taco Tuesday',
    address: '222 El Cajon Blvd',
    phone_number: '',
    website_url: '',
    happy_hour_times: 'Tuesday: 3:00 PM - 5:00 PM | Wednesday: 3:00 PM - 5:00 PM',
    regular_hours: '',
    rating: '4.2',
    review_count: '80',
    price_level: 'PRICE_LEVEL_INEXPENSIVE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
  },
  {
    restaurant_name: 'No HH Diner',
    address: '333 Main St',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: '',
    rating: '4.0',
    review_count: '50',
    price_level: 'PRICE_LEVEL_INEXPENSIVE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
  },
  {
    restaurant_name: 'Sushi Palace',
    address: '444 Oak St',
    phone_number: '',
    website_url: '',
    happy_hour_times: 'Monday: 5:00 PM - 7:00 PM | Friday: 5:00 PM - 7:00 PM',
    regular_hours: '',
    rating: '4.8',
    review_count: '200',
    price_level: 'PRICE_LEVEL_EXPENSIVE',
    source: 'google_maps_api',
    freshness_date: '2026-04-20',
  },
];

function switchToList() {
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
}

describe('HappyHourFinder - Filter Combinations', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Given search "Sushi" and Has happy hour checked, When both filters are active, Then only "Sushi Monday" and "Sushi Palace" are shown (both have happy hours)', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');
    fireEvent.change(searchInput, { target: { value: 'Sushi' } });

    await waitFor(() => {
      expect(screen.getByText('Sushi Monday')).toBeInTheDocument();
      // Sushi Palace is active now (5 PM), so it stays
      expect(screen.getByText('Sushi Palace')).toBeInTheDocument();
      expect(screen.queryByText('Taco Tuesday')).not.toBeInTheDocument();
      expect(screen.queryByText('No HH Diner')).not.toBeInTheDocument();
    });
  });

  it('Given day is set to Tuesday and Has happy hour checked, When filters are active, Then places WITH any happy hour data are shown', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    const daySelect = screen.getByLabelText('Day');
    fireEvent.change(daySelect, { target: { value: 'Tuesday' } });

    await waitFor(() => {
      // Sushi Monday HAS happy hour data (Monday/Wednesday) → shown
      expect(screen.getByText('Sushi Monday')).toBeInTheDocument();
      // Taco Tuesday HAS happy hour data → shown
      expect(screen.getByText('Taco Tuesday')).toBeInTheDocument();
      // No HH Diner has NO happy hour data → hidden
      expect(screen.queryByText('No HH Diner')).not.toBeInTheDocument();
      // Sushi Palace HAS happy hour data → shown
      expect(screen.getByText('Sushi Palace')).toBeInTheDocument();
    });
  });

  it('Given search "Sushi", day is Tuesday, and Happy hour now checked, When all three filters are active, Then zero places are shown and "No places found" appears', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    fireEvent.change(screen.getByPlaceholderText('Restaurant name or address...'), {
      target: { value: 'Sushi' },
    });
    fireEvent.change(screen.getByLabelText('Day'), { target: { value: 'Tuesday' } });
    fireEvent.click(screen.getByLabelText('Happy hour now'));

    await waitFor(() => {
      // Sushi Monday has no Tuesday HH, Sushi Palace has no Tuesday HH -> none shown
      expect(screen.queryByText('Sushi Monday')).not.toBeInTheDocument();
      expect(screen.queryByText('Sushi Palace')).not.toBeInTheDocument();
      expect(screen.getByText('No places found.')).toBeInTheDocument();
      expect(screen.getByText(/Try changing your search or filters/i)).toBeInTheDocument();
    });
  });

  it('Given search query is cleared after filtering, When input is emptied, Then all restaurants matching other active filters are shown again', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');
    fireEvent.change(searchInput, { target: { value: 'Sushi' } });

    await waitFor(() => {
      expect(screen.queryByText('Taco Tuesday')).not.toBeInTheDocument();
    });

    fireEvent.change(searchInput, { target: { value: '' } });

    await waitFor(() => {
      // With Has happy hour still checked: Sushi Monday, Taco Tuesday, Sushi Palace shown
      // No HH Diner hidden
      expect(screen.getByText('Sushi Monday')).toBeInTheDocument();
      expect(screen.getByText('Taco Tuesday')).toBeInTheDocument();
      expect(screen.queryByText('No HH Diner')).not.toBeInTheDocument();
      expect(screen.getByText('Sushi Palace')).toBeInTheDocument();
    });
  });

  it('Given search matches address but not name, When filtering, Then the restaurant is included in results', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    const searchInput = screen.getByPlaceholderText('Restaurant name or address...');
    fireEvent.change(searchInput, { target: { value: 'El Cajon' } });

    await waitFor(() => {
      expect(screen.getByText('Taco Tuesday')).toBeInTheDocument();
      expect(screen.queryByText('Sushi Monday')).not.toBeInTheDocument();
    });
  });

  it('Given results count is displayed, When search query is active, Then the count text includes the search term', async () => {
    render(<HappyHourFinder restaurants={mockRestaurants} />);
    switchToList();

    fireEvent.change(screen.getByPlaceholderText('Restaurant name or address...'), {
      target: { value: 'Sushi' },
    });

    await waitFor(() => {
      // Two sushi restaurants, both have happy hours
      expect(screen.getByText(/Showing 2 places/i)).toBeInTheDocument();
    });
  });
});
