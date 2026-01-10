/**
 * Tests for useBrowseScrollRestoration hook.
 *
 * Story 10.7: Scroll position restoration for browse tab.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useBrowseScrollRestoration,
  getSavedScrollState,
  BROWSE_SCROLL_KEY,
} from './use-browse-scroll-restoration';

describe('useBrowseScrollRestoration', () => {
  // Mock sessionStorage
  const mockSessionStorage = {
    store: {} as Record<string, string>,
    getItem: vi.fn((key: string) => mockSessionStorage.store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      mockSessionStorage.store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete mockSessionStorage.store[key];
    }),
    clear: vi.fn(() => {
      mockSessionStorage.store = {};
    }),
    key: vi.fn(),
    length: 0,
  };

  // Mock window.scrollTo and scrollY
  const originalScrollTo = window.scrollTo;
  const originalScrollY = Object.getOwnPropertyDescriptor(window, 'scrollY');

  beforeEach(() => {
    vi.clearAllMocks();
    mockSessionStorage.store = {};

    // Setup sessionStorage mock
    Object.defineProperty(window, 'sessionStorage', {
      value: mockSessionStorage,
      writable: true,
    });

    // Setup scroll mocks
    window.scrollTo = vi.fn();
    Object.defineProperty(window, 'scrollY', {
      value: 0,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    window.scrollTo = originalScrollTo;
    if (originalScrollY) {
      Object.defineProperty(window, 'scrollY', originalScrollY);
    }
  });

  describe('savePosition', () => {
    it('saves current scroll position and page to sessionStorage', () => {
      Object.defineProperty(window, 'scrollY', { value: 500, configurable: true });

      const { result } = renderHook(() => useBrowseScrollRestoration());

      act(() => {
        result.current.savePosition(3);
      });

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        BROWSE_SCROLL_KEY,
        JSON.stringify({ scrollY: 500, page: 3 })
      );
    });

    it('saves page 1 when no page specified', () => {
      Object.defineProperty(window, 'scrollY', { value: 200, configurable: true });

      const { result } = renderHook(() => useBrowseScrollRestoration());

      act(() => {
        result.current.savePosition();
      });

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        BROWSE_SCROLL_KEY,
        JSON.stringify({ scrollY: 200, page: 1 })
      );
    });
  });

  describe('restorePosition', () => {
    it('returns saved position and page from sessionStorage', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = JSON.stringify({
        scrollY: 750,
        page: 4,
      });

      const { result } = renderHook(() => useBrowseScrollRestoration());

      const restored = result.current.restorePosition();

      expect(restored).toEqual({ scrollY: 750, page: 4 });
    });

    it('returns null when no saved position exists', () => {
      const { result } = renderHook(() => useBrowseScrollRestoration());

      const restored = result.current.restorePosition();

      expect(restored).toBeNull();
    });

    it('returns null when sessionStorage contains invalid JSON', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = 'invalid json';

      const { result } = renderHook(() => useBrowseScrollRestoration());

      const restored = result.current.restorePosition();

      expect(restored).toBeNull();
    });

    it('clears saved position after restoring', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = JSON.stringify({
        scrollY: 300,
        page: 2,
      });

      const { result } = renderHook(() => useBrowseScrollRestoration());

      result.current.restorePosition();

      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith(BROWSE_SCROLL_KEY);
    });
  });

  describe('clearPosition', () => {
    it('removes saved position from sessionStorage', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = JSON.stringify({
        scrollY: 100,
        page: 1,
      });

      const { result } = renderHook(() => useBrowseScrollRestoration());

      act(() => {
        result.current.clearPosition();
      });

      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith(BROWSE_SCROLL_KEY);
    });
  });

  describe('scrollToPosition', () => {
    it('scrolls window to saved position', () => {
      const { result } = renderHook(() => useBrowseScrollRestoration());

      act(() => {
        result.current.scrollToPosition(600);
      });

      expect(window.scrollTo).toHaveBeenCalledWith({
        top: 600,
        behavior: 'instant',
      });
    });

    it('uses instant behavior by default', () => {
      const { result } = renderHook(() => useBrowseScrollRestoration());

      act(() => {
        result.current.scrollToPosition(400);
      });

      expect(window.scrollTo).toHaveBeenCalledWith({
        top: 400,
        behavior: 'instant',
      });
    });
  });

  describe('getSavedScrollState', () => {
    it('returns saved state without consuming it', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = JSON.stringify({
        scrollY: 500,
        page: 3,
      });

      const state = getSavedScrollState();

      expect(state).toEqual({ scrollY: 500, page: 3 });
      // Should NOT have removed the item
      expect(mockSessionStorage.removeItem).not.toHaveBeenCalled();
    });

    it('returns null when no saved state exists', () => {
      const state = getSavedScrollState();

      expect(state).toBeNull();
    });

    it('returns null for invalid JSON', () => {
      mockSessionStorage.store[BROWSE_SCROLL_KEY] = 'invalid json';

      const state = getSavedScrollState();

      expect(state).toBeNull();
    });
  });
});
