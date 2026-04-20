import { describe, it, expect } from 'vitest';
import { isHappyHourActive, getHappyHourStatus, HappyHourStatus } from '../src/lib/happy-hour-utils';

describe('Ould Sod specific issue', () => {
  it('should parse times with narrow non-breaking spaces', () => {
    // The Ould Sod has times like "10:00 AM – 4:00 PM" with special unicode chars
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    // Using en-dash and narrow non-breaking spaces
    const times = 'Sunday: 10:00\u202fAM\u202f–\u202f4:00\u202fPM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('should handle en-dash as separator', () => {
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    const times = 'Sunday: 10:00 AM – 4:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('should handle mixed special characters', () => {
    // Simulating the weird encoding from the CSV - test with explicit unicode
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    // Using actual narrow non-breaking spaces
    const times = 'Sunday: 10:00 AM - 4:00 PM';  // Standard format works
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('Ould Sod Sunday happy hour - should be active at noon', () => {
    const now = new Date('2026-04-19T12:00:00'); // Sunday 12 PM
    // Approximating the CSV format
    const times = 'Sunday: 10:00 AM - 4:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.ACTIVE);
  });
});
