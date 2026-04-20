import { describe, it, expect } from 'vitest';
import { isHappyHourActive, getHappyHourStatus, HappyHourStatus } from '../src/lib/happy-hour-utils';

describe('Inherited AM/PM handling', () => {
  it('treats start time as PM when end time is PM', () => {
    // Sunday 4:00 PM, happy hour is "3 - 6 PM" (should be 3 PM - 6 PM)
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3:00 - 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('treats start time as AM when end time is AM', () => {
    // Sunday 10:00 AM, happy hour is "9 - 11 AM" (should be 9 AM - 11 AM)
    const now = new Date('2026-04-19T10:00:00'); // Sunday 10 AM
    const times = 'Sunday: 9:00 - 11:00 AM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('treats "3 - 6 PM" as 3 PM - 6 PM', () => {
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3 - 6 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('shows LATER_TODAY when before start without AM/PM', () => {
    // Sunday 2:00 PM, happy hour is "3 - 6 PM"
    const now = new Date('2026-04-19T14:00:00'); // Sunday 2 PM
    const times = 'Sunday: 3:00 - 6:00 PM';
    
    const status = getHappyHourStatus(times, now);
    expect(status).toBe(HappyHourStatus.LATER_TODAY);
  });

  it('shows PASSED_TODAY when after end without AM/PM', () => {
    // Sunday 7:00 PM, happy hour is "3 - 6 PM"
    const now = new Date('2026-04-19T19:00:00'); // Sunday 7 PM
    const times = 'Sunday: 3:00 - 6:00 PM';
    
    const status = getHappyHourStatus(times, now);
    expect(status).toBe(HappyHourStatus.PASSED_TODAY);
  });

  it('handles reverse end time without AM/PM (like 10 PM - 12 AM)', () => {
    // Sunday 11:00 PM, happy hour is "10 - 12 AM"
    const now = new Date('2026-04-19T23:00:00'); // Sunday 11 PM
    const times = 'Sunday: 10:00 - 12:00 AM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('preserves explicit AM/PM on start time', () => {
    // Sunday 9:00 AM, happy hour is "9 AM - 12 PM" (start has AM, should stay AM)
    const now = new Date('2026-04-19T09:00:00'); // Sunday 9 AM
    const times = 'Sunday: 9 AM - 12 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });
});
