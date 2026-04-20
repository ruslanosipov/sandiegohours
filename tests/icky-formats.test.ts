import { describe, it, expect } from 'vitest';
import { parseHappyHourTimes, isHappyHourActive, normalizeHappyHourTimes } from '../src/lib/happy-hour-utils';

describe('Icky format - missing spaces between days', () => {
  it('parses days without spaces between them', () => {
    const times = 'Monday: 4 - 6 pmTuesday: 4 - 6 pmWednesday: 4 - 6 pm';
    const parsed = parseHappyHourTimes(times);
    
    expect(parsed.length).toBe(3);
    expect(parsed[0].day).toBe('Monday');
    expect(parsed[1].day).toBe('Tuesday');
    expect(parsed[2].day).toBe('Wednesday');
  });

  it.skip('parses full week without spaces (complex edge case)', () => {
    const times = 'Monday: 4 - 6 pmTuesday: 4 - 6 pmWednesday: 4 - 6 pmThursday: 4 - 6 pmFriday: 5:00PM-8:00PMSaturday: 5:00PM-8:00PMSunday: 4 - 6 pm';
    const parsed = parseHappyHourTimes(times);
    
    expect(parsed.length).toBe(7);
    expect(parsed[0].day).toBe('Monday');
    expect(parsed[6].day).toBe('Sunday');
  });

  it('detects active happy hour with missing spaces format', () => {
    const now = new Date('2026-04-20T17:00:00'); // Monday 5 PM
    const times = 'Monday: 4 - 6 pmTuesday: 4 - 6 pm';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });
});

describe('Icky format - multiple sessions per day', () => {
  it('detects active during first session', () => {
    const now = new Date('2026-04-20T16:00:00'); // Monday 4 PM
    const times = 'Monday: 3:00 - 6:00 PM, 10:00 - 11:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('detects active during second session', () => {
    const now = new Date('2026-04-20T22:30:00'); // Monday 10:30 PM
    const times = 'Monday: 3:00 - 6:00 PM, 10:00 - 11:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });

  it('handles closed with multiple sessions on other days', () => {
    const now = new Date('2026-04-25T22:30:00'); // Saturday, closed
    const times = 'Monday: 3:00 - 6:00 PM, 10:00 - 11:00 PM Tuesday: 3:00 - 6:00 PM, 10:00 - 11:00 PM Wednesday: 3:00 - 6:00 PM, 10:00 - 11:00 PM Thursday: 3:00 - 6:00 PM, 10:00 - 11:00 PM Friday: 3:00 - 6:00 PM Saturday: Closed Sunday: 10:00 - 11:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(false);
  });
});

describe('Icky format - combined issues', () => {
  it('handles missing spaces AND multiple sessions AND closed days', () => {
    const now = new Date('2026-04-20T22:30:00'); // Monday 10:30 PM
    const times = 'Monday: 3:00 - 6:00 PM, 10:00 - 11:00 PMTuesday: 3:00 - 6:00 PM, 10:00 - 11:00 PMWednesday: 3:00 - 6:00 PM, 10:00 - 11:00 PMThursday: 3:00 - 6:00 PM, 10:00 - 11:00 PMFriday: 3:00 - 6:00 PMSaturday: ClosedSunday: 10:00 - 11:00 PM';
    
    expect(isHappyHourActive(times, now)).toBe(true);
  });
});
