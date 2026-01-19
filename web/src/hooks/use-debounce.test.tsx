import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from './use-debounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial value', () => {
    it('returns initial value immediately on first render', () => {
      const { result } = renderHook(() => useDebounce('initial', 300));

      expect(result.current).toBe('initial');
    });

    it('handles different types - string', () => {
      const { result } = renderHook(() => useDebounce('test', 300));

      expect(result.current).toBe('test');
    });

    it('handles different types - number', () => {
      const { result } = renderHook(() => useDebounce(42, 300));

      expect(result.current).toBe(42);
    });

    it('handles different types - boolean', () => {
      const { result } = renderHook(() => useDebounce(true, 300));

      expect(result.current).toBe(true);
    });

    it('handles different types - object', () => {
      const obj = { foo: 'bar' };
      const { result } = renderHook(() => useDebounce(obj, 300));

      expect(result.current).toBe(obj);
    });

    it('handles different types - array', () => {
      const arr = [1, 2, 3];
      const { result } = renderHook(() => useDebounce(arr, 300));

      expect(result.current).toEqual(arr);
    });
  });

  describe('default delay', () => {
    it('uses 300ms as default delay when not specified', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value),
        { initialProps: { value: 'initial' } }
      );

      expect(result.current).toBe('initial');

      // Update value
      act(() => {
        rerender({ value: 'updated' });
      });

      // Should not update immediately
      expect(result.current).toBe('initial');

      // Advance timers by 299ms (just before default delay)
      act(() => {
        vi.advanceTimersByTime(299);
      });
      expect(result.current).toBe('initial');

      // Advance by 1 more ms to complete 300ms
      act(() => {
        vi.advanceTimersByTime(1);
      });

      expect(result.current).toBe('updated');
    });
  });

  describe('custom delay', () => {
    it('debounces value updates by the specified delay', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: 'initial' } }
      );

      expect(result.current).toBe('initial');

      // Update value
      act(() => {
        rerender({ value: 'updated' });
      });

      // Should not update immediately
      expect(result.current).toBe('initial');

      // Advance timers by 500ms
      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(result.current).toBe('updated');
    });

    it('works with very short delay (50ms)', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 50),
        { initialProps: { value: 'initial' } }
      );

      act(() => {
        rerender({ value: 'updated' });
      });

      expect(result.current).toBe('initial');

      act(() => {
        vi.advanceTimersByTime(50);
      });

      expect(result.current).toBe('updated');
    });

    it('works with long delay (2000ms)', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 2000),
        { initialProps: { value: 'initial' } }
      );

      act(() => {
        rerender({ value: 'updated' });
      });

      expect(result.current).toBe('initial');

      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(result.current).toBe('updated');
    });
  });

  describe('rapid value changes', () => {
    it('only emits the last value after rapid changes', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 'v1' } }
      );

      // Rapid changes - each change resets the timer
      act(() => {
        rerender({ value: 'v2' });
      });
      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        rerender({ value: 'v3' });
      });
      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        rerender({ value: 'v4' });
      });
      act(() => {
        vi.advanceTimersByTime(100);
      });

      // Still showing initial because timer keeps being reset
      expect(result.current).toBe('v1');

      // Complete the delay from last update (300ms total from v4)
      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(result.current).toBe('v4');
    });

    it('resets timer on each value change', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 'initial' } }
      );

      act(() => {
        // First change
        rerender({ value: 'change1' });
        vi.advanceTimersByTime(200);

        // Second change (resets timer)
        rerender({ value: 'change2' });
        vi.advanceTimersByTime(200);

        // Third change (resets timer again)
        rerender({ value: 'change3' });
      });

      // Still showing initial because timer keeps resetting
      expect(result.current).toBe('initial');

      // Now let it complete
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(result.current).toBe('change3');
    });
  });

  describe('zero delay edge case', () => {
    it('handles zero delay', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 0),
        { initialProps: { value: 'initial' } }
      );

      act(() => {
        rerender({ value: 'updated' });
      });

      // With 0 delay, should update after event loop
      act(() => {
        vi.advanceTimersByTime(0);
      });

      expect(result.current).toBe('updated');
    });
  });

  describe('cleanup on unmount', () => {
    it('clears timeout when component unmounts', () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      const { unmount } = renderHook(() => useDebounce('test', 300));

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('does not update after unmount', () => {
      const { result, rerender, unmount } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 'initial' } }
      );

      act(() => {
        rerender({ value: 'updated' });
      });

      // Unmount before timer completes
      unmount();

      // Advance timers
      act(() => {
        vi.advanceTimersByTime(300);
      });

      // Should still be initial (no update after unmount)
      expect(result.current).toBe('initial');
    });
  });

  describe('delay changes', () => {
    it('handles delay prop changes', () => {
      const { result, rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: 'initial', delay: 300 } }
      );

      // Update value and delay
      act(() => {
        rerender({ value: 'updated', delay: 500 });
      });

      expect(result.current).toBe('initial');

      // Advance by new delay (500ms)
      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(result.current).toBe('updated');
    });
  });

  describe('type preservation', () => {
    it('preserves string type', () => {
      const { result } = renderHook(() => useDebounce('test', 300));

      const value: string = result.current;
      expect(typeof value).toBe('string');
    });

    it('preserves number type', () => {
      const { result } = renderHook(() => useDebounce(42, 300));

      const value: number = result.current;
      expect(typeof value).toBe('number');
    });

    it('preserves complex object type', () => {
      interface TestObject {
        id: number;
        name: string;
      }

      const testObj: TestObject = { id: 1, name: 'test' };
      const { result } = renderHook(() => useDebounce(testObj, 300));

      const value: TestObject = result.current;
      expect(value).toHaveProperty('id');
      expect(value).toHaveProperty('name');
    });
  });

  describe('practical use case - search input', () => {
    it('simulates search input debouncing', () => {
      const { result, rerender } = renderHook(
        ({ searchTerm }) => useDebounce(searchTerm, 300),
        { initialProps: { searchTerm: '' } }
      );

      act(() => {
        // User types "r"
        rerender({ searchTerm: 'r' });
        vi.advanceTimersByTime(100);

        // User types "e"
        rerender({ searchTerm: 're' });
        vi.advanceTimersByTime(100);

        // User types "a"
        rerender({ searchTerm: 'rea' });
        vi.advanceTimersByTime(100);

        // User types "c"
        rerender({ searchTerm: 'reac' });
        vi.advanceTimersByTime(100);

        // User types "t"
        rerender({ searchTerm: 'react' });
      });

      // Still showing empty because timer kept resetting
      expect(result.current).toBe('');

      // User stops typing, timer completes
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(result.current).toBe('react');
    });
  });
});
