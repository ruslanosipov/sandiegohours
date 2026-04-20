import { describe, it, expect } from 'vitest';
import { hasHappyHour, formatPriceLevel, parseHappyHourTimes } from '../src/lib/happy-hour-utils';
import { HappyHourPlace } from '../src/types/happy-hour';

describe('hasHappyHour', () => {
  it('returns true when happy_hour_times is set', () => {
    const place: HappyHourPlace = {
      restaurant_name: 'Test Restaurant',
      address: '123 Test St',
      phone_number: '',
      website_url: '',
      happy_hour_times: 'Monday: 3:00 - 6:00 PM',
      regular_hours: '',
      rating: '4.5',
      review_count: '100',
      price_level: 'PRICE_LEVEL_MODERATE',
      source: 'test',
      freshness_date: '2026-01-01',
    };
    expect(hasHappyHour(place)).toBe(true);
  });

  it('returns false when happy_hour_times is empty', () => {
    const place: HappyHourPlace = {
      restaurant_name: 'Test Restaurant',
      address: '123 Test St',
      phone_number: '',
      website_url: '',
      happy_hour_times: '',
      regular_hours: '',
      rating: '4.5',
      review_count: '100',
      price_level: 'PRICE_LEVEL_MODERATE',
      source: 'test',
      freshness_date: '2026-01-01',
    };
    expect(hasHappyHour(place)).toBe(false);
  });

  it('returns false when happy_hour_times is only whitespace', () => {
    const place: HappyHourPlace = {
      restaurant_name: 'Test Restaurant',
      address: '123 Test St',
      phone_number: '',
      website_url: '',
      happy_hour_times: '   ',
      regular_hours: '',
      rating: '4.5',
      review_count: '100',
      price_level: 'PRICE_LEVEL_MODERATE',
      source: 'test',
      freshness_date: '2026-01-01',
    };
    expect(hasHappyHour(place)).toBe(false);
  });
});

describe('formatPriceLevel', () => {
  it('returns $ for inexpensive', () => {
    expect(formatPriceLevel('PRICE_LEVEL_INEXPENSIVE')).toBe('$');
  });

  it('returns $$ for moderate', () => {
    expect(formatPriceLevel('PRICE_LEVEL_MODERATE')).toBe('$$');
  });

  it('returns $$$ for expensive', () => {
    expect(formatPriceLevel('PRICE_LEVEL_EXPENSIVE')).toBe('$$$');
  });

  it('returns $$$$ for very expensive', () => {
    expect(formatPriceLevel('PRICE_LEVEL_VERY_EXPENSIVE')).toBe('$$$$');
  });

  it('returns empty string for unknown', () => {
    expect(formatPriceLevel('')).toBe('');
  });
});

describe('parseHappyHourTimes', () => {
  it('parses single day happy hour', () => {
    const result = parseHappyHourTimes('Monday: 3:00 - 6:00 PM');
    expect(result).toHaveLength(1);
    expect(result[0].day).toBe('Monday');
    expect(result[0].startTime).toBe('3:00 PM');
    expect(result[0].endTime).toBe('6:00 PM');
  });

  it('parses multiple days separated by pipe', () => {
    const result = parseHappyHourTimes('Monday: 3:00 - 6:00 PM | Tuesday: 3:00 - 6:00 PM');
    expect(result).toHaveLength(2);
    expect(result[0].day).toBe('Monday');
    expect(result[1].day).toBe('Tuesday');
  });

  it('handles closed days', () => {
    const result = parseHappyHourTimes('Monday: Closed');
    expect(result).toHaveLength(1);
    expect(result[0].day).toBe('Monday');
    expect(result[0].startTime).toBe('');
    expect(result[0].endTime).toBe('');
  });

  it('returns empty array for empty string', () => {
    const result = parseHappyHourTimes('');
    expect(result).toHaveLength(0);
  });
});
