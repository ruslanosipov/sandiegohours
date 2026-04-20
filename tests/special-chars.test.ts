import { describe, it, expect } from 'vitest';
import { normalizeTimeFormat } from '../src/lib/happy-hour-utils';

describe.skip('Special character handling', () => {
  it('handles narrow non-breaking space (\u202f)', () => {
    const result = normalizeTimeFormat('10:00\u202fAM');
    expect(result).toBe('10:00 AM');
  });

  it('handles en-dash (\u2013) as separator', () => {
    const result = normalizeTimeFormat('10:00 AM – 4:00 PM');
    expect(result).toBe('10:00 AM - 4:00 PM');
  });

  it('handles em-dash', () => {
    const result = normalizeTimeFormat('10:00 AM — 4:00 PM');
    expect(result).toBe('10:00 AM - 4:00 PM');
  });

  it('handles non-breaking space (\u00a0)', () => {
    const result = normalizeTimeFormat('10:00\u00a0AM');
    expect(result).toBe('10:00 AM');
  });
});
