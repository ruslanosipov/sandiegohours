import { describe, it, expect } from 'vitest';
import { 
  getHappyHourStatus, 
  isHappyHourActive, 
  parseTimeToMinutes,
  HappyHourStatus 
} from '../src/lib/happy-hour-utils';

describe('Happy Hour Status - parseTimeToMinutes', () => {
  it('parses AM times correctly', () => {
    expect(parseTimeToMinutes('9:00 AM')).toBe(540);
    expect(parseTimeToMinutes('12:00 PM')).toBe(720);
    expect(parseTimeToMinutes('3:00 AM')).toBe(180);
  });

  it('parses PM times correctly', () => {
    expect(parseTimeToMinutes('3:00 PM')).toBe(900);
    expect(parseTimeToMinutes('6:00 PM')).toBe(1080);
    expect(parseTimeToMinutes('11:59 PM')).toBe(1439);
  });

  it('handles midnight', () => {
    expect(parseTimeToMinutes('12:00 AM')).toBe(0);
    expect(parseTimeToMinutes('12:30 AM')).toBe(30);
  });

  it('handles edge cases', () => {
    expect(parseTimeToMinutes('1:30 PM')).toBe(810);
    expect(parseTimeToMinutes('10:45 PM')).toBe(1365);
  });
});

describe('Happy Hour Status - isHappyHourActive', () => {
  it('returns true when current time is within happy hour', () => {
    // Sunday 4:00 PM, Hangout happy hour is 3-6 PM
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('returns false when current time is before happy hour', () => {
    // Sunday 2:00 PM, Hangout happy hour is 3-6 PM
    const now = new Date('2026-04-19T14:00:00'); // Sunday 2 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(false);
  });

  it('returns false when current time is after happy hour', () => {
    // Sunday 7:00 PM, Hangout happy hour is 3-6 PM
    const now = new Date('2026-04-19T19:00:00'); // Sunday 7 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(false);
  });

  it('returns false for different day', () => {
    // Monday 4:00 PM, Hangout happy hour is Sunday only
    const now = new Date('2026-04-20T16:00:00'); // Monday 4 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(false);
  });

  it('handles multiple days in schedule', () => {
    // Sunday 4:00 PM, schedule has Sunday
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM | Monday: 4:00 PM - 7:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('handles late night happy hours (past midnight)', () => {
    // 11:30 PM, happy hour is 10 PM - 12 AM
    const now = new Date('2026-04-19T23:30:00'); // Sunday 11:30 PM
    const times = 'Sunday: 10:00 PM - 12:00 AM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('returns false for empty happy hour times', () => {
    const now = new Date('2026-04-19T16:00:00');
    expect(isHappyHourActive('', now)).toBe(false);
  });
});

describe('Happy Hour Status - getHappyHourStatus', () => {
  it('returns ACTIVE when happy hour is currently happening', () => {
    const now = new Date('2026-04-19T16:00:00'); // Sunday 4 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.ACTIVE);
  });

  it('returns NO_HAPPY_HOUR when no happy hour is scheduled', () => {
    const now = new Date('2026-04-19T16:00:00');
    const times = '';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.NO_HAPPY_HOUR);
  });

  it('returns LATER_TODAY when happy hour will happen later', () => {
    const now = new Date('2026-04-19T10:00:00'); // Sunday 10 AM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.LATER_TODAY);
  });

  it('returns PASSED_TODAY when happy hour already ended', () => {
    const now = new Date('2026-04-19T19:00:00'); // Sunday 7 PM
    const times = 'Sunday: 3:00 PM - 6:00 PM';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.PASSED_TODAY);
  });

  it('returns LATER_TODAY when happy hour is on a different day', () => {
    // Monday 4 PM, happy hour is Tuesday
    const now = new Date('2026-04-20T16:00:00'); // Monday 4 PM
    const times = 'Tuesday: 3:00 PM - 6:00 PM';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.LATER_TODAY);
  });

  it('returns ACTIVE correctly across midnight', () => {
    const now = new Date('2026-04-19T23:30:00'); // Sunday 11:30 PM
    const times = 'Sunday: 10:00 PM - 12:00 AM';
    
    expect(getHappyHourStatus(times, now)).toBe(HappyHourStatus.ACTIVE);
  });
});

describe('Happy Hour Status - day of week matching', () => {
  it('correctly identifies Sunday', () => {
    const now = new Date('2026-04-19T16:00:00'); // Sunday
    expect(now.getDay()).toBe(0);
  });

  it('correctly identifies Monday', () => {
    const now = new Date('2026-04-20T16:00:00'); // Monday
    expect(now.getDay()).toBe(1);
  });
});
