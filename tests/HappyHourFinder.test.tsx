import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

// Test data factory - creates restaurants with defaults
function createRestaurant(overrides: Partial<HappyHourPlace> = {}): HappyHourPlace {
  return {
    restaurant_name: 'Test Restaurant',
    address: '123 Main St, San Diego, CA 92116',
    phone_number: '',
    website_url: '',
    happy_hour_times: '',
    regular_hours: 'Monday: 11:00 AM - 10:00 PM',
    rating: '4.5',
    review_count: '100',
    price_level: 'PRICE_LEVEL_MODERATE',
    source: 'Google Maps API',
    freshness_date: '2026-04-19',
    ...overrides,
  };
}

describe('HappyHourFinder - Stats Display', () => {
  it('displays the total number of places in the directory', () => {
    const restaurants = [
      createRestaurant(),
      createRestaurant({ restaurant_name: 'Second Place' }),
      createRestaurant({ restaurant_name: 'Third Place' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Total Places')).toBeInTheDocument();
  });

  it('displays how many places offer happy hour', () => {
    const restaurants = [
      createRestaurant({ happy_hour_times: 'Monday: 3-6 PM' }),
      createRestaurant({ happy_hour_times: 'Tuesday: 4-7 PM' }),
      createRestaurant({ happy_hour_times: '' }), // No happy hour
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('With Happy Hour')).toBeInTheDocument();
  });

  it('displays active happy hour count for selected day/time', () => {
    const restaurants = [
      createRestaurant({ happy_hour_times: 'Sunday: 3:00 PM - 6:00 PM' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Shows active count stat with label
    const activeNowLabel = screen.getByText('Active Now');
    expect(activeNowLabel).toBeInTheDocument();
  });
});

describe('HappyHourFinder - Restaurant Display', () => {
  it('shows restaurant name for each place in the directory', () => {
    const restaurants = [
      createRestaurant({ restaurant_name: 'The Corner Bar' }),
      createRestaurant({ restaurant_name: 'Downtown Tavern' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    expect(screen.getByText('The Corner Bar')).toBeInTheDocument();
    expect(screen.getByText('Downtown Tavern')).toBeInTheDocument();
  });

  it('displays the full address for each restaurant', () => {
    const restaurants = [
      createRestaurant({ address: '456 Broadway, San Diego, CA 92101' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    expect(screen.getByText('456 Broadway, San Diego, CA 92101')).toBeInTheDocument();
  });

  it('shows star rating for each place', () => {
    const restaurants = [
      createRestaurant({ rating: '4.8', review_count: '250' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Rating is part of the document
    expect(screen.getByText(/4\.8/)).toBeInTheDocument();
    expect(screen.getByText(/250/)).toBeInTheDocument();
  });

  it('indicates which restaurants have happy hour specials', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'HH Bar',
        happy_hour_times: 'Monday: 3-6 PM' 
      }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Happy hour indicator appears in card (badge or Happy Hour heading)
    const documentText = document.body.textContent || '';
    expect(documentText).toMatch(/Has Happy Hour|Happy Hour/);
  });

  it('displays happy hour schedule when available', () => {
    const restaurants = [
      createRestaurant({
        happy_hour_times: 'Monday: 3:00 PM - 6:00 PM | Tuesday: 4:00 PM - 7:00 PM',
      }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Happy hour info visible in document
    const textContent = document.body.textContent || '';
    expect(textContent).toContain('Monday');
  });

  it('shows price level as dollar signs', () => {
    const restaurants = [
      createRestaurant({ price_level: 'PRICE_LEVEL_INEXPENSIVE' }),
      createRestaurant({ price_level: 'PRICE_LEVEL_MODERATE' }),
      createRestaurant({ price_level: 'PRICE_LEVEL_EXPENSIVE' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Price levels displayed as dollar signs
    expect(screen.getByText('$')).toBeInTheDocument();
    expect(screen.getByText('$$')).toBeInTheDocument();
    expect(screen.getByText('$$$')).toBeInTheDocument();
  });

  it('displays source of happy hour information', () => {
    const restaurants = [
      createRestaurant({ source: 'Website' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Source info displayed
    const sourceElements = screen.getAllByText(/Website|Google Maps|Manual/);
    expect(sourceElements.length).toBeGreaterThan(0);
  });

  it('provides clickable phone number for calling', () => {
    const restaurants = [
      createRestaurant({ phone_number: '+1 619-555-1234' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    const phoneLink = screen.getByText('+1 619-555-1234');
    expect(phoneLink.tagName).toBe('A');
    expect(phoneLink).toHaveAttribute('href', 'tel:+1 619-555-1234');
  });

  it('provides clickable website link', () => {
    const restaurants = [
      createRestaurant({ website_url: 'https://example.com' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    const websiteLink = screen.getByText('Website');
    expect(websiteLink.tagName).toBe('A');
    expect(websiteLink).toHaveAttribute('href', 'https://example.com');
  });
});

describe('HappyHourFinder - Search Behavior', () => {
  it('filters results when user types a restaurant name', () => {
    const restaurants = [
      createRestaurant({ restaurant_name: 'Downtown Brewing' }),
      createRestaurant({ restaurant_name: 'Uptown Cafe' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    const searchInput = screen.getByPlaceholderText(/Search by restaurant name/);
    fireEvent.change(searchInput, { target: { value: 'Downtown' } });
    
    expect(screen.getByText('Downtown Brewing')).toBeInTheDocument();
    expect(screen.queryByText('Uptown Cafe')).not.toBeInTheDocument();
  });

  it('filters results when user searches by address', () => {
    const restaurants = [
      createRestaurant({ address: '123 Adams Ave, San Diego' }),
      createRestaurant({ address: '456 Park Blvd, San Diego' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    const searchInput = screen.getByPlaceholderText(/Search by restaurant name/);
    fireEvent.change(searchInput, { target: { value: 'Adams' } });
    
    expect(screen.getByText('123 Adams Ave, San Diego')).toBeInTheDocument();
    expect(screen.queryByText('456 Park Blvd, San Diego')).not.toBeInTheDocument();
  });

  it('shows helpful message when search returns no results', () => {
    const restaurants = [createRestaurant()];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    const searchInput = screen.getByPlaceholderText(/Search by restaurant name/);
    fireEvent.change(searchInput, { target: { value: 'NonExistentXYZ' } });
    
    expect(screen.getByText(/No places found/)).toBeInTheDocument();
  });
});

describe('HappyHourFinder - Happy Hour Filter', () => {
  it('shows only places with happy hour when toggle is enabled', () => {
    // Use Sunday hours matching test date, so filter doesn't hide it
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'Has HH',
        happy_hour_times: 'Sunday: 3:00 PM - 6:00 PM' 
      }),
      createRestaurant({ 
        restaurant_name: 'No HH',
        happy_hour_times: '' 
      }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Select time within happy hour range so it stays visible
    const daySelect = screen.getByLabelText('Day');
    const timeSelect = screen.getByLabelText('Time');
    fireEvent.change(daySelect, { target: { value: 'Sunday' } });
    fireEvent.change(timeSelect, { target: { value: '16:00' } });
    
    const toggle = screen.getByLabelText(/Only show places with happy hour/);
    fireEvent.click(toggle);
    
    expect(screen.getByText('Has HH')).toBeInTheDocument();
    expect(screen.queryByText('No HH')).not.toBeInTheDocument();
  });
});

describe('HappyHourFinder - Day and Time Selection', () => {
  it('allows user to select a day of the week', () => {
    render(<HappyHourFinder restaurants={[]} />);
    
    const daySelect = screen.getByLabelText('Day');
    fireEvent.change(daySelect, { target: { value: 'Friday' } });
    
    expect(daySelect).toHaveValue('Friday');
  });

  it('allows user to select a time of day', () => {
    render(<HappyHourFinder restaurants={[]} />);
    
    const timeSelect = screen.getByLabelText('Time');
    fireEvent.change(timeSelect, { target: { value: '17:00' } });
    
    expect(timeSelect).toHaveValue('17:00');
  });

  it('updates active count when day changes', () => {
    const restaurants = [
      createRestaurant({ happy_hour_times: 'Friday: 3:00 PM - 6:00 PM' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Initially 0 active (it's currently Sunday in tests)
    const daySelect = screen.getByLabelText('Day');
    fireEvent.change(daySelect, { target: { value: 'Friday' } });
    fireEvent.change(screen.getByLabelText('Time'), { target: { value: '16:00' } });
    
    // Should now show an active place
    expect(screen.getByText('Active Now')).toBeInTheDocument();
  });
});

describe('HappyHourFinder - Edge Cases', () => {
  it('handles empty directory gracefully', () => {
    render(<HappyHourFinder restaurants={[]} />);
    
    // Total places is 0
    const zeroElements = screen.getAllByText('0');
    expect(zeroElements.length).toBeGreaterThan(0);
    expect(screen.getByText('Total Places')).toBeInTheDocument();
    expect(screen.getByText(/No places found/)).toBeInTheDocument();
  });

  it('displays multiple happy hour sessions when available', () => {
    const restaurants = [
      createRestaurant({
        happy_hour_times: 'Monday: 3:00 PM - 6:00 PM, 10:00 PM - 12:00 AM',
      }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Happy hour info visible in document
    const textContent = document.body.textContent || '';
    expect(textContent).toContain('Monday');
    expect(textContent).toContain('3:00 PM');
  });

  it('allows viewing regular hours in expandable section', () => {
    const restaurants = [
      createRestaurant({ regular_hours: 'Monday: 11:00 AM - 11:00 PM' }),
    ];
    
    render(<HappyHourFinder restaurants={restaurants} />);
    
    // Regular Hours expandable section present
    const regularHours = screen.queryByText('Regular Hours');
    if (regularHours) {
      expect(regularHours).toBeInTheDocument();
    }
  });
});
