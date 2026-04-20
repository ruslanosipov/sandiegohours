import { describe, it, expect } from 'vitest';
import { hasHappyHour, formatPriceLevel, parseHappyHourTimes } from '../src/lib/happy-hour-utils';
import { HappyHourPlace } from '../src/types/happy-hour';

describe('hasHappyHour', () => {
  it('should return true when happy_hour_times contains valid data', () => {
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

  it('should return false when happy_hour_times is empty string', () => {
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

  it('should return false when happy_hour_times is only whitespace', () => {
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
  it('should return single $ for inexpensive price level', () => {
    expect(formatPriceLevel('PRICE_LEVEL_INEXPENSIVE')).toBe('$');
  });

  it('should return $$ for moderate price level', () => {
    expect(formatPriceLevel('PRICE_LEVEL_MODERATE')).toBe('$$');
  });

  it('should return $$$ for expensive price level', () => {
    expect(formatPriceLevel('PRICE_LEVEL_EXPENSIVE')).toBe('$$$');
  });

  it('should return $$$$ for very expensive price level', () => {
    expect(formatPriceLevel('PRICE_LEVEL_VERY_EXPENSIVE')).toBe('$$$$');
  });

  it('should return empty string for unknown price level', () => {
    expect(formatPriceLevel('')).toBe('');
  });
});

describe('parseHappyHourTimes', () => {
  it('should extract day and time range from single day happy hour string', () => {
    const result = parseHappyHourTimes('Monday: 3:00 - 6:00 PM');
    expect(result).toHaveLength(1);
    expect(result[0].day).toBe('Monday');
    expect(result[0].startTime).toBe('3:00');
    expect(result[0].endTime).toBe('6:00 PM');
  });

  it('should parse multiple days when separated by pipe character', () => {
    const result = parseHappyHourTimes('Monday: 3:00 - 6:00 PM | Tuesday: 3:00 - 6:00 PM');
    expect(result).toHaveLength(2);
    expect(result[0].day).toBe('Monday');
    expect(result[1].day).toBe('Tuesday');
  });

  it('should mark closed days with empty start and end times', () => {
    const result = parseHappyHourTimes('Monday: Closed');
    expect(result).toHaveLength(1);
    expect(result[0].day).toBe('Monday');
    expect(result[0].startTime).toBe('');
    expect(result[0].endTime).toBe('');
  });

  it('should return empty array for empty input string', () => {
    const result = parseHappyHourTimes('');
    expect(result).toHaveLength(0);
  });

  it('should handle double sessions separated by comma', () => {
    const result = parseHappyHourTimes('Monday: 3:00 - 6:00 PM, 10:00 - 11:00 PM');
    expect(result).toHaveLength(1);
    expect(result[0].day).toBe('Monday');
    expect(result[0].startTime).toBe('3:00');
    expect(result[0].endTime).toBe('6:00 PM');
    expect(result[0].isSecondSession).toBe(true);
    expect(result[0].startTime2).toBe('10:00');
    expect(result[0].endTime2).toBe('11:00 PM');
  });

  it('should handle en-dash character in time ranges', () => {
    const result = parseHappyHourTimes('Monday: 3:00 – 6:00 PM');
    expect(result).toHaveLength(1);
    expect(result[0].startTime).toBe('3:00');
    expect(result[0].endTime).toBe('6:00 PM');
  });
});
