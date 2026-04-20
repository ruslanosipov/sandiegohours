import { describe, it, expect } from 'vitest';
import { normalizeTimeFormat, parseFlexibleTime } from '../src/lib/happy-hour-utils';

describe('normalizeTimeFormat', () => {
  it('converts lowercase am/pm to uppercase with space', () => {
    expect(normalizeTimeFormat('3:00 pm')).toBe('3:00 PM');
    expect(normalizeTimeFormat('4:30 am')).toBe('4:30 AM');
  });

  it('adds space before AM/PM when missing', () => {
    expect(normalizeTimeFormat('3:00pm')).toBe('3:00 PM');
    expect(normalizeTimeFormat('4:30AM')).toBe('4:30 AM');
  });

  it('handles hours without minutes', () => {
    expect(normalizeTimeFormat('3 pm')).toBe('3:00 PM');
    expect(normalizeTimeFormat('4pm')).toBe('4:00 PM');
    expect(normalizeTimeFormat('10am')).toBe('10:00 AM');
  });

  it('handles single digit hours', () => {
    expect(normalizeTimeFormat('3:00 PM')).toBe('3:00 PM');
    expect(normalizeTimeFormat('9:30 AM')).toBe('9:30 AM');
  });

  it('normalizes midnight and noon', () => {
    expect(normalizeTimeFormat('12:00 AM')).toBe('12:00 AM');
    expect(normalizeTimeFormat('12:00 PM')).toBe('12:00 PM');
    expect(normalizeTimeFormat('12am')).toBe('12:00 AM');
    expect(normalizeTimeFormat('12pm')).toBe('12:00 PM');
  });

  it('handles various whitespace', () => {
    expect(normalizeTimeFormat('3:00  PM')).toBe('3:00 PM');
    expect(normalizeTimeFormat('4:00PM')).toBe('4:00 PM');
  });

  it('returns already formatted times unchanged', () => {
    expect(normalizeTimeFormat('3:00 PM')).toBe('3:00 PM');
    expect(normalizeTimeFormat('10:30 AM')).toBe('10:30 AM');
    expect(normalizeTimeFormat('12:45 PM')).toBe('12:45 PM');
  });
});

describe('parseFlexibleTime', () => {
  it('parses various time formats to minutes', () => {
    expect(parseFlexibleTime('3:00 PM')).toBe(900);
    expect(parseFlexibleTime('3:00 pm')).toBe(900);
    expect(parseFlexibleTime('3pm')).toBe(900);
    expect(parseFlexibleTime('3 pm')).toBe(900);
    expect(parseFlexibleTime('15:00')).toBe(900);
  });

  it('parses AM times', () => {
    expect(parseFlexibleTime('9:00 AM')).toBe(540);
    expect(parseFlexibleTime('9am')).toBe(540);
    expect(parseFlexibleTime('9:30 am')).toBe(570);
  });

  it('handles 24-hour format', () => {
    expect(parseFlexibleTime('15:00')).toBe(900);
    expect(parseFlexibleTime('09:30')).toBe(570);
    expect(parseFlexibleTime('00:00')).toBe(0);
    expect(parseFlexibleTime('23:59')).toBe(1439);
  });

  it('handles midnight and noon edge cases', () => {
    expect(parseFlexibleTime('12:00 AM')).toBe(0);
    expect(parseFlexibleTime('12:00 PM')).toBe(720);
    expect(parseFlexibleTime('12 AM')).toBe(0);
    expect(parseFlexibleTime('12 PM')).toBe(720);
    expect(parseFlexibleTime('12am')).toBe(0);
    expect(parseFlexibleTime('12pm')).toBe(720);
  });

  it('handles various inconsistent formats', () => {
    expect(parseFlexibleTime('3pm')).toBe(900);
    expect(parseFlexibleTime('3:00pm')).toBe(900);
    expect(parseFlexibleTime('3:00  PM')).toBe(900);
    expect(parseFlexibleTime('3:00PM')).toBe(900);
  });
});
