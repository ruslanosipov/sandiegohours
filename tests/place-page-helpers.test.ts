import { describe, it, expect } from 'vitest';
import {
  simplifyAddress,
  formatDate,
  formatSource,
  getTodayName,
} from '../src/app/places/[placeId]/helpers';

describe('simplifyAddress', () => {
  it('removes San Diego, CA and zip code', () => {
    expect(simplifyAddress('123 Main St, San Diego, CA 92104, USA')).toBe('123 Main St, USA');
  });

  it('removes just CA at end', () => {
    expect(simplifyAddress('456 Oak St, San Diego, CA')).toBe('456 Oak St, San Diego');
  });

  it('returns empty string for empty input', () => {
    expect(simplifyAddress('')).toBe('');
  });

  it('handles full 9-digit zip', () => {
    expect(simplifyAddress('789 Pine St, San Diego, CA 92104-1234')).toBe('789 Pine St');
  });

  it('leaves address unchanged when no city match', () => {
    expect(simplifyAddress('100 Broadway, New York, NY 10001')).toBe('100 Broadway, New York, NY 10001');
  });
});

describe('formatDate', () => {
  it('formats ISO date to locale string', () => {
    // Use a timezone-aware string so the test passes regardless of the runner's timezone
    expect(formatDate('2026-01-15T12:00:00')).toBe('Jan 15, 2026');
  });

  it('returns empty string for empty input', () => {
    expect(formatDate('')).toBe('');
  });

  it('returns original string for invalid date', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date');
  });
});

describe('formatSource', () => {
  it('recognizes Google Places API', () => {
    expect(formatSource('Google Places API (Happy Hours)')).toBe('Google Maps');
  });

  it('recognizes Website/AI source', () => {
    expect(formatSource('Website (AI parsed)')).toBe('Website');
  });

  it('recognizes Manual', () => {
    expect(formatSource('Manual')).toBe('Manual');
  });

  it('returns original for unknown source', () => {
    expect(formatSource('Other Source')).toBe('Other Source');
  });

  it('returns Unknown for empty', () => {
    expect(formatSource('')).toBe('Unknown');
  });
});

describe('getTodayName', () => {
  it('returns a valid weekday name', () => {
    const result = getTodayName();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    expect(days).toContain(result);
  });
});
