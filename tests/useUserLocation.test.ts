import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { useUserLocation } from '../src/hooks/useUserLocation';

describe.skip('useUserLocation Hook', () => {
  const mockGeolocation = {
    getCurrentPosition: vi.fn(),
  };

  beforeEach(() => {
    vi.stubGlobal('navigator', {
      geolocation: mockGeolocation,
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts with no location and not loading', () => {
    const Wrapper = ({ children }: { children: React.ReactNode }) => React.createElement('div', null, children);
    const { result } = renderHook(() => useUserLocation(), { wrapper: Wrapper });

    expect(result.current.location).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });
});
