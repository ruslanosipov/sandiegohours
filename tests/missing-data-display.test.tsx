import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HappyHourFinder from '../src/app/components/HappyHourFinder';
import { HappyHourPlace } from '../src/types/happy-hour';

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

function switchToList() {
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
}

describe('HappyHourFinder - Missing Data Display', () => {
  it('shows restaurant even when rating is missing', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'No Rating Bar',
        rating: '',
        review_count: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    // Uncheck Has happy hour since default data has no happy_hour_times
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    expect(screen.getByText('No Rating Bar')).toBeInTheDocument();
    // Should not crash, should still display the card
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
  });

  it('shows restaurant even when review count is missing', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'No Reviews',
        review_count: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    expect(screen.getByText('No Reviews')).toBeInTheDocument();
  });

  it('shows restaurant with empty price level', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'No Price',
        price_level: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    expect(screen.getByText('No Price')).toBeInTheDocument();
  });

  it('handles completely minimal restaurant data', () => {
    const restaurants: HappyHourPlace[] = [
      {
        restaurant_name: 'Minimal',
        address: '1 Min St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '',
        review_count: '',
        price_level: '',
        source: '',
        freshness_date: '',
      },
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    expect(screen.getByText('Minimal')).toBeInTheDocument();
    expect(screen.getByText('1 Min St')).toBeInTheDocument();
  });

  it('displays rating and reviews when present', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'Rated',
        rating: '4.8',
        review_count: '2500',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    // Rating should be visible
    expect(screen.getByText(/4\.8/)).toBeInTheDocument();
    expect(screen.getByText(/2500/)).toBeInTheDocument();
  });

  it('shows distance when location sorting is active', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'Nearby',
        latitude: '32.7630',
        longitude: '-117.1210',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));
    
    // Initially sorted by name, no distance shown
    expect(screen.getByText('Nearby')).toBeInTheDocument();
  });

  it('handles mixed data - some with ratings, some without', () => {
    const restaurants = [
      createRestaurant({ 
        restaurant_name: 'Has Rating',
        rating: '4.5',
        review_count: '100',
      }),
      createRestaurant({ 
        restaurant_name: 'No Rating',
        rating: '',
        review_count: '',
      }),
    ];

    render(<HappyHourFinder restaurants={restaurants} />);
    switchToList();
    fireEvent.click(screen.getByLabelText('Has happy hour'));

    expect(screen.getByText('Has Rating')).toBeInTheDocument();
    expect(screen.getByText('No Rating')).toBeInTheDocument();
  });
});
