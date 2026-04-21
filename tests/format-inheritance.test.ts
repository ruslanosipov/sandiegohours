import { describe, it, expect } from 'vitest';
import { normalizeHappyHourTimes } from '../src/lib/happy-hour-utils';

describe('Inherit AM/PM for single hour numbers', () => {
  it('converts "2 - 7:00 PM" to "2:00 PM - 7:00 PM" (both PM)', () => {
    const input = 'Friday: 2 - 7:00 PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Friday: 2:00 PM - 7:00 PM');
  });

  it('converts "3 - 5 PM" to "3:00 PM - 5:00 PM" (both PM)', () => {
    const input = 'Monday: 3 - 5 PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Monday: 3:00 PM - 5:00 PM');
  });

  it('converts "9 - 11 AM" to "9:00 AM - 11:00 AM" (both AM)', () => {
    const input = 'Sunday: 9 - 11 AM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Sunday: 9:00 AM - 11:00 AM');
  });

  it('keeps explicit AM/PM on first time', () => {
    const input = 'Monday: 10:00 AM - 2:00 PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Monday: 10:00 AM - 2:00 PM');
  });
});

describe('Handle HTML content', () => {
  it('returns empty/no happy hour for HTML content', () => {
    const input = '<div class="sqs-html-content">...</div>';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('');
  });

  it('returns empty for just HTML tags', () => {
    const input = '<h4>Happy Hour</h4>';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('');
  });
});
