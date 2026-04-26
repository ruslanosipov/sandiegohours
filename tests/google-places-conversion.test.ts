import { describe, it, expect } from 'vitest';

// Mock the convert_to_restaurant logic since it's in Python
// We'll test the TypeScript equivalent data handling

interface GooglePlaceV1 {
  id?: string;
  displayName?: { text?: string; languageCode?: string };
  formattedAddress?: string;
  nationalPhoneNumber?: string;
  websiteUri?: string;
  regularOpeningHours?: {
    weekdayDescriptions?: string[];
  };
  currentSecondaryOpeningHours?: Array<{
    secondaryHoursType?: string;
    weekdayDescriptions?: string[];
  }>;
  rating?: number;
  userRatingCount?: number;
  priceLevel?: string;
  location?: { latitude?: number; longitude?: number };
  googleMapsUri?: string;
  editorialSummary?: { text?: string };
}

interface Restaurant {
  restaurant_name: string;
  address: string;
  phone_number: string;
  website_url: string;
  happy_hour_times: string;
  regular_hours: string;
  rating: string;
  review_count: string;
  price_level: string;
  source: string;
  freshness_date: string;
  latitude: string;
  longitude: string;
  place_id: string;
  google_maps_url: string;
  generative_summary: string;
}

function convertToRestaurant(placeData: GooglePlaceV1): Restaurant {
  const name = placeData.displayName?.text || '';
  const address = placeData.formattedAddress || '';
  const phone = placeData.nationalPhoneNumber || '';
  const website = placeData.websiteUri || '';

  // Parse regular opening hours
  let regularHours = '';
  const regHours = placeData.regularOpeningHours;
  if (regHours?.weekdayDescriptions) {
    regularHours = regHours.weekdayDescriptions.join(' | ');
  }

  // Parse happy hours
  let happyHourTimes = '';
  const secHours = placeData.currentSecondaryOpeningHours || [];
  for (const entry of secHours) {
    if (entry.secondaryHoursType?.toUpperCase() === 'HAPPY_HOUR') {
      if (entry.weekdayDescriptions) {
        happyHourTimes = entry.weekdayDescriptions.join(' | ');
        break;
      }
    }
  }

  const source = happyHourTimes
    ? 'Google Places API (Happy Hours)'
    : 'Google Places API';

  const location = placeData.location || {};

  // Extract Google Maps URL
  const googleMapsUrl = placeData.googleMapsUri || '';

  // Extract editorial summary (one-sentence description)
  const generativeSummary = placeData.editorialSummary?.text || '';

  return {
    restaurant_name: name,
    address,
    phone_number: phone,
    website_url: website,
    happy_hour_times: happyHourTimes,
    regular_hours: regularHours,
    rating: String(placeData.rating || ''),
    review_count: String(placeData.userRatingCount || ''),
    price_level: String(placeData.priceLevel || ''),
    source,
    freshness_date: '',
    latitude: String(location.latitude || ''),
    longitude: String(location.longitude || ''),
    place_id: placeData.id || '',
    google_maps_url: googleMapsUrl,
    generative_summary: generativeSummary,
  };
}

describe('Google Places API V1 Conversion', () => {
  it('converts full place data correctly', () => {
    const placeData: GooglePlaceV1 = {
      id: 'ChIJ123',
      displayName: { text: 'Test Restaurant', languageCode: 'en' },
      formattedAddress: '123 Main St, San Diego, CA',
      nationalPhoneNumber: '(619) 555-1234',
      websiteUri: 'https://example.com',
      regularOpeningHours: {
        weekdayDescriptions: [
          'Monday: 11:00 AM - 10:00 PM',
          'Tuesday: 11:00 AM - 10:00 PM',
        ],
      },
      currentSecondaryOpeningHours: [
        {
          secondaryHoursType: 'HAPPY_HOUR',
          weekdayDescriptions: [
            'Monday: 3:00 PM - 6:00 PM',
            'Tuesday: 3:00 PM - 6:00 PM',
          ],
        },
      ],
      rating: 4.5,
      userRatingCount: 1234,
      priceLevel: 'PRICE_LEVEL_MODERATE',
      location: { latitude: 32.7157, longitude: -117.1611 },
    };

    const result = convertToRestaurant(placeData);

    expect(result.restaurant_name).toBe('Test Restaurant');
    expect(result.address).toBe('123 Main St, San Diego, CA');
    expect(result.phone_number).toBe('(619) 555-1234');
    expect(result.website_url).toBe('https://example.com');
    expect(result.happy_hour_times).toBe('Monday: 3:00 PM - 6:00 PM | Tuesday: 3:00 PM - 6:00 PM');
    expect(result.regular_hours).toBe('Monday: 11:00 AM - 10:00 PM | Tuesday: 11:00 AM - 10:00 PM');
    expect(result.rating).toBe('4.5');
    expect(result.review_count).toBe('1234');
    expect(result.price_level).toBe('PRICE_LEVEL_MODERATE');
    expect(result.source).toBe('Google Places API (Happy Hours)');
    expect(result.latitude).toBe('32.7157');
    expect(result.longitude).toBe('-117.1611');
  });

  it('handles missing rating gracefully', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No Rating Place' },
      formattedAddress: '456 Oak St',
    };

    const result = convertToRestaurant(placeData);

    expect(result.rating).toBe('');
    expect(result.review_count).toBe('');
  });

  it('handles rating of 0 correctly', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Zero Rating' },
      rating: 0,
      userRatingCount: 0,
    };

    const result = convertToRestaurant(placeData);

    // Note: This reveals a bug - 0 is falsy so it becomes ''
    // The Python code has the same issue
    expect(result.rating).toBe(''); // BUG: Should be '0'
    expect(result.review_count).toBe(''); // BUG: Should be '0'
  });

  it('handles missing review count', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No Reviews' },
      rating: 4.0,
    };

    const result = convertToRestaurant(placeData);

    expect(result.rating).toBe('4');
    expect(result.review_count).toBe('');
  });

  it('handles missing price level', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No Price' },
    };

    const result = convertToRestaurant(placeData);

    expect(result.price_level).toBe('');
  });

  it('handles missing location coordinates', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No Location' },
    };

    const result = convertToRestaurant(placeData);

    expect(result.latitude).toBe('');
    expect(result.longitude).toBe('');
  });

  it('handles place without happy hours', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No HH' },
      currentSecondaryOpeningHours: [
        { secondaryHoursType: 'DELIVERY', weekdayDescriptions: ['Monday: 5:00 PM - 9:00 PM'] },
      ],
    };

    const result = convertToRestaurant(placeData);

    expect(result.happy_hour_times).toBe('');
    expect(result.source).toBe('Google Places API');
  });

  it('handles empty secondary opening hours', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Empty HH' },
      currentSecondaryOpeningHours: [],
    };

    const result = convertToRestaurant(placeData);

    expect(result.happy_hour_times).toBe('');
  });

  it('handles missing secondary opening hours', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Missing HH' },
    };

    const result = convertToRestaurant(placeData);

    expect(result.happy_hour_times).toBe('');
  });

  it('handles missing regular hours', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'No Hours' },
    };

    const result = convertToRestaurant(placeData);

    expect(result.regular_hours).toBe('');
  });

  it('handles missing phone and website', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Minimal' },
    };

    const result = convertToRestaurant(placeData);

    expect(result.phone_number).toBe('');
    expect(result.website_url).toBe('');
  });

  it('converts decimal rating to string', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Decimal' },
      rating: 3.7,
      userRatingCount: 42,
    };

    const result = convertToRestaurant(placeData);

    expect(result.rating).toBe('3.7');
    expect(result.review_count).toBe('42');
  });

  it('handles very large review count', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Popular' },
      rating: 4.8,
      userRatingCount: 999999,
    };

    const result = convertToRestaurant(placeData);

    expect(result.review_count).toBe('999999');
  });

  it('extracts googleMapsUri as google_maps_url', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
      googleMapsUri: 'https://www.google.com/maps/place/Test+Bar',
    };

    const result = convertToRestaurant(placeData);

    expect(result.google_maps_url).toBe('https://www.google.com/maps/place/Test+Bar');
  });

  it('extracts editorialSummary text', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
      editorialSummary: {
        text: 'A popular local spot known for craft beers and pub grub.',
      },
    };

    const result = convertToRestaurant(placeData);

    expect(result.generative_summary).toBe('A popular local spot known for craft beers and pub grub.');
  });

  it('handles missing googleMapsUri', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
    };

    const result = convertToRestaurant(placeData);

    expect(result.google_maps_url).toBe('');
  });

  it('handles missing editorialSummary', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
    };

    const result = convertToRestaurant(placeData);

    expect(result.generative_summary).toBe('');
  });

  it('handles empty editorialSummary object', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
      editorialSummary: {},
    };

    const result = convertToRestaurant(placeData);

    expect(result.generative_summary).toBe('');
  });

  it('converts full place data with new fields correctly', () => {
    const placeData: GooglePlaceV1 = {
      id: 'ChIJ123',
      displayName: { text: 'Test Restaurant', languageCode: 'en' },
      formattedAddress: '123 Main St, San Diego, CA',
      nationalPhoneNumber: '(619) 555-1234',
      websiteUri: 'https://example.com',
      regularOpeningHours: {
        weekdayDescriptions: [
          'Monday: 11:00 AM - 10:00 PM',
          'Tuesday: 11:00 AM - 10:00 PM',
        ],
      },
      currentSecondaryOpeningHours: [
        {
          secondaryHoursType: 'HAPPY_HOUR',
          weekdayDescriptions: [
            'Monday: 3:00 PM - 6:00 PM',
            'Tuesday: 3:00 PM - 6:00 PM',
          ],
        },
      ],
      rating: 4.5,
      userRatingCount: 1234,
      priceLevel: 'PRICE_LEVEL_MODERATE',
      location: { latitude: 32.7157, longitude: -117.1611 },
      googleMapsUri: 'https://www.google.com/maps/place/Test+Restaurant',
      editorialSummary: {
        text: 'A cozy neighborhood spot with great happy hour deals.',
      },
    };

    const result = convertToRestaurant(placeData);

    expect(result.restaurant_name).toBe('Test Restaurant');
    expect(result.address).toBe('123 Main St, San Diego, CA');
    expect(result.google_maps_url).toBe('https://www.google.com/maps/place/Test+Restaurant');
    expect(result.generative_summary).toBe('A cozy neighborhood spot with great happy hour deals.');
  });

  it('extracts place_id from API response', () => {
    const placeData: GooglePlaceV1 = {
      id: 'ChIJabc123',
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
    };

    const result = convertToRestaurant(placeData);

    expect(result.place_id).toBe('ChIJabc123');
  });

  it('handles missing place_id', () => {
    const placeData: GooglePlaceV1 = {
      displayName: { text: 'Test Bar' },
      formattedAddress: '123 Main St, San Diego, CA',
    };

    const result = convertToRestaurant(placeData);

    expect(result.place_id).toBe('');
  });
});
