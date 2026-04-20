import { describe, it, expect } from 'vitest';
import { calculateDistance, sortByDistance, formatDistance } from '../src/lib/distance-utils';
import { HappyHourPlace } from '../src/types/happy-hour';

describe('Distance Utils - calculateDistance', () => {
  it('calculates distance between two coordinates in miles', () => {
    // San Diego to Los Angeles (approx 111 miles)
    const sanDiego = { lat: 32.7157, lng: -117.1611 };
    const losAngeles = { lat: 34.0522, lng: -118.2437 };
    
    const distance = calculateDistance(sanDiego.lat, sanDiego.lng, losAngeles.lat, losAngeles.lng);
    
    // Should be approximately 111 miles (within 5% tolerance)
    expect(distance).toBeGreaterThan(100);
    expect(distance).toBeLessThan(120);
  });

  it('returns 0 for same coordinates', () => {
    const distance = calculateDistance(32.7157, -117.1611, 32.7157, -117.1611);
    expect(distance).toBe(0);
  });

  it('calculates small distances accurately', () => {
    // Two points about 0.1 miles apart in San Diego
    const point1 = { lat: 32.7157, lng: -117.1611 };
    const point2 = { lat: 32.7167, lng: -117.1611 };
    
    const distance = calculateDistance(point1.lat, point1.lng, point2.lat, point2.lng);
    
    // Should be around 0.07 miles (about 370 feet)
    expect(distance).toBeGreaterThan(0.05);
    expect(distance).toBeLessThan(0.1);
  });
});

describe('Distance Utils - formatDistance', () => {
  it('formats distance less than 0.1 miles in feet', () => {
    expect(formatDistance(0.05)).toBe('264 ft');
    expect(formatDistance(0.02)).toBe('106 ft');
  });

  it('formats distance between 0.1 and 10 miles with 1 decimal', () => {
    expect(formatDistance(0.5)).toBe('0.5 mi');
    expect(formatDistance(1.23)).toBe('1.2 mi');
    expect(formatDistance(5.67)).toBe('5.7 mi');
  });

  it('formats distance over 10 miles as whole number', () => {
    expect(formatDistance(12.34)).toBe('12 mi');
    expect(formatDistance(100.9)).toBe('101 mi');
  });

  it('handles zero distance', () => {
    expect(formatDistance(0)).toBe('0 ft');
  });
});

describe('Distance Utils - sortByDistance', () => {
  const userLocation = { lat: 32.7157, lng: -117.1611 }; // San Diego

  it('sorts restaurants by distance from user', () => {
    const restaurants: HappyHourPlace[] = [
      {
        restaurant_name: 'Far Place',
        address: '123 Main St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '32.7150', // Very close
        longitude: '-117.1600',
      },
      {
        restaurant_name: 'Close Place',
        address: '456 Near St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '33.0', // Farther away (~20 miles)
        longitude: '-117.0',
      },
    ];

    const sorted = sortByDistance(restaurants, userLocation.lat, userLocation.lng);

    expect(sorted[0].restaurant_name).toBe('Far Place');
    expect(sorted[1].restaurant_name).toBe('Close Place');
  });

  it('places restaurants without coordinates at the end', () => {
    const restaurants: HappyHourPlace[] = [
      {
        restaurant_name: 'No Coords',
        address: '123 Main St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
      },
      {
        restaurant_name: 'Has Coords',
        address: '456 Near St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '32.7150',
        longitude: '-117.1600',
      },
    ];

    const sorted = sortByDistance(restaurants, userLocation.lat, userLocation.lng);

    expect(sorted[0].restaurant_name).toBe('Has Coords');
    expect(sorted[1].restaurant_name).toBe('No Coords');
  });

  it('preserves original array order for places with same distance', () => {
    const restaurants: HappyHourPlace[] = [
      {
        restaurant_name: 'First',
        address: '123 Main St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '32.7157',
        longitude: '-117.1611',
      },
      {
        restaurant_name: 'Second',
        address: '456 Near St',
        phone_number: '',
        website_url: '',
        happy_hour_times: '',
        regular_hours: '',
        rating: '4.0',
        review_count: '10',
        price_level: 'PRICE_LEVEL_MODERATE',
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '32.7157',
        longitude: '-117.1611',
      },
    ];

    const sorted = sortByDistance(restaurants, userLocation.lat, userLocation.lng);

    expect(sorted[0].restaurant_name).toBe('First');
    expect(sorted[1].restaurant_name).toBe('Second');
  });

  it('calculates and assigns distance to each restaurant', () => {
    const restaurants: HappyHourPlace[] = [
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
        source: 'Google Maps API',
        freshness_date: '2026-04-19',
        latitude: '32.7150',
        longitude: '-117.1600',
      },
    ];

    const sorted = sortByDistance(restaurants, userLocation.lat, userLocation.lng);

    expect(sorted[0].distance).toBeDefined();
    expect(typeof sorted[0].distance).toBe('number');
    expect(sorted[0].distance).toBeGreaterThan(0);
  });
});
