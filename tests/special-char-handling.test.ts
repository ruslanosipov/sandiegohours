import { describe, it, expect } from 'vitest';
import { isHappyHourActive, getHappyHourStatus, HappyHourStatus, normalizeHappyHourTimes } from '../src/lib/happy-hour-utils';

describe('Special character handling - narrow non-breaking spaces', () => {
  it('should parse times with narrow non-breaking spaces (\u202f)', () => {
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    const times = 'Sunday: 10:00\u202fAM\u202f-\u202f4:00\u202fPM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('normalizes narrow non-breaking spaces to regular spaces', () => {
    const input = 'Monday: 3:00\u202fPM\u202f-\u202f6:00\u202fPM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Monday: 3:00 PM - 6:00 PM');
  });
});

describe('Special character handling - en-dash and em-dash', () => {
  it('should handle en-dash (\u2013) as time separator', () => {
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3:00 PM \u2013 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('should handle em-dash (\u2014) as time separator', () => {
    const now = new Date('2026-04-19T16:00:00');
    const times = 'Sunday: 3:00 PM \u2014 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('normalizes en-dash to regular hyphen in output', () => {
    const input = 'Monday: 3:00 PM \u2013 6:00 PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Monday: 3:00 PM - 6:00 PM');
  });
});

describe('Special character handling - non-breaking space', () => {
  it('handles non-breaking space (\u00a0)', () => {
    const now = new Date('2026-04-19T16:00:00');
    const times = 'Sunday: 3:00\u00a0PM - 6:00\u00a0PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });
});

describe('Special character handling - mixed unicode whitespace', () => {
  it('handles various unicode whitespace characters', () => {
    const input = 'Monday:\u20003:00\u2009PM\u200a-\u200b6:00\u2002PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Monday: 3:00 PM - 6:00 PM');
  });
});

describe('Special character handling - Ould Sod real-world case', () => {
  it('handles Sunday 10 AM - 4 PM format correctly', () => {
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    const times = 'Sunday: 10:00 AM - 4:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.ACTIVE);
  });

  it('normalizes Ould Sod format consistently', () => {
    const input = 'Sunday: 10:00 AM - 4:00 PM';
    const result = normalizeHappyHourTimes(input);
    expect(result).toBe('Sunday: 10:00 AM - 4:00 PM');
  });
});
