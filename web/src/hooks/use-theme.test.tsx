import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useTheme } from './use-theme';

// Mock next-themes
const mockUseNextTheme = vi.fn();
vi.mock('next-themes', () => ({
  useTheme: () => mockUseNextTheme(),
}));

describe('useTheme', () => {
  describe('theme value passthrough', () => {
    it('returns theme from next-themes', () => {
      mockUseNextTheme.mockReturnValue({
        theme: 'dark',
        setTheme: vi.fn(),
        systemTheme: 'dark',
        resolvedTheme: 'dark',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.theme).toBe('dark');
    });

    it('returns systemTheme from next-themes', () => {
      mockUseNextTheme.mockReturnValue({
        theme: 'system',
        setTheme: vi.fn(),
        systemTheme: 'light',
        resolvedTheme: 'light',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.systemTheme).toBe('light');
    });

    it('returns resolvedTheme from next-themes', () => {
      mockUseNextTheme.mockReturnValue({
        theme: 'system',
        setTheme: vi.fn(),
        systemTheme: 'dark',
        resolvedTheme: 'dark',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.resolvedTheme).toBe('dark');
    });
  });

  describe('setTheme function passthrough', () => {
    it('passes through setTheme function', () => {
      const mockSetTheme = vi.fn();
      mockUseNextTheme.mockReturnValue({
        theme: 'light',
        setTheme: mockSetTheme,
        systemTheme: 'light',
        resolvedTheme: 'light',
      });

      const { result } = renderHook(() => useTheme());

      result.current.setTheme('dark');

      expect(mockSetTheme).toHaveBeenCalledWith('dark');
    });
  });

  describe('computed properties', () => {
    describe('isDark property', () => {
      it('returns true when resolvedTheme is "dark"', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'dark',
          setTheme: vi.fn(),
          systemTheme: 'dark',
          resolvedTheme: 'dark',
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isDark).toBe(true);
      });

      it('returns false when resolvedTheme is "light"', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'light',
          setTheme: vi.fn(),
          systemTheme: 'light',
          resolvedTheme: 'light',
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isDark).toBe(false);
      });

      it('returns false when resolvedTheme is undefined', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'system',
          setTheme: vi.fn(),
          systemTheme: undefined,
          resolvedTheme: undefined,
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isDark).toBe(false);
      });
    });

    describe('isLight property', () => {
      it('returns true when resolvedTheme is "light"', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'light',
          setTheme: vi.fn(),
          systemTheme: 'light',
          resolvedTheme: 'light',
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isLight).toBe(true);
      });

      it('returns false when resolvedTheme is "dark"', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'dark',
          setTheme: vi.fn(),
          systemTheme: 'dark',
          resolvedTheme: 'dark',
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isLight).toBe(false);
      });

      it('returns false when resolvedTheme is undefined', () => {
        mockUseNextTheme.mockReturnValue({
          theme: 'system',
          setTheme: vi.fn(),
          systemTheme: undefined,
          resolvedTheme: undefined,
        });

        const { result } = renderHook(() => useTheme());

        expect(result.current.isLight).toBe(false);
      });
    });

    describe('toggleTheme function', () => {
      it('toggles from dark to light', () => {
        const mockSetTheme = vi.fn();
        mockUseNextTheme.mockReturnValue({
          theme: 'dark',
          setTheme: mockSetTheme,
          systemTheme: 'dark',
          resolvedTheme: 'dark',
        });

        const { result } = renderHook(() => useTheme());

        result.current.toggleTheme();

        expect(mockSetTheme).toHaveBeenCalledWith('light');
      });

      it('toggles from light to dark', () => {
        const mockSetTheme = vi.fn();
        mockUseNextTheme.mockReturnValue({
          theme: 'light',
          setTheme: mockSetTheme,
          systemTheme: 'light',
          resolvedTheme: 'light',
        });

        const { result } = renderHook(() => useTheme());

        result.current.toggleTheme();

        expect(mockSetTheme).toHaveBeenCalledWith('dark');
      });

      it('uses resolvedTheme for toggle logic, not theme', () => {
        const mockSetTheme = vi.fn();
        // theme is 'system' but resolvedTheme is 'dark'
        mockUseNextTheme.mockReturnValue({
          theme: 'system',
          setTheme: mockSetTheme,
          systemTheme: 'dark',
          resolvedTheme: 'dark',
        });

        const { result } = renderHook(() => useTheme());

        result.current.toggleTheme();

        // Should toggle based on resolvedTheme (dark), not theme (system)
        expect(mockSetTheme).toHaveBeenCalledWith('light');
      });
    });
  });

  describe('system theme detection', () => {
    it('handles system theme with dark preference', () => {
      mockUseNextTheme.mockReturnValue({
        theme: 'system',
        setTheme: vi.fn(),
        systemTheme: 'dark',
        resolvedTheme: 'dark',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.theme).toBe('system');
      expect(result.current.systemTheme).toBe('dark');
      expect(result.current.resolvedTheme).toBe('dark');
      expect(result.current.isDark).toBe(true);
      expect(result.current.isLight).toBe(false);
    });

    it('handles system theme with light preference', () => {
      mockUseNextTheme.mockReturnValue({
        theme: 'system',
        setTheme: vi.fn(),
        systemTheme: 'light',
        resolvedTheme: 'light',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.theme).toBe('system');
      expect(result.current.systemTheme).toBe('light');
      expect(result.current.resolvedTheme).toBe('light');
      expect(result.current.isDark).toBe(false);
      expect(result.current.isLight).toBe(true);
    });
  });

  describe('return value structure', () => {
    it('returns all expected properties', () => {
      const mockSetTheme = vi.fn();
      mockUseNextTheme.mockReturnValue({
        theme: 'dark',
        setTheme: mockSetTheme,
        systemTheme: 'dark',
        resolvedTheme: 'dark',
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current).toHaveProperty('theme');
      expect(result.current).toHaveProperty('setTheme');
      expect(result.current).toHaveProperty('systemTheme');
      expect(result.current).toHaveProperty('resolvedTheme');
      expect(result.current).toHaveProperty('isDark');
      expect(result.current).toHaveProperty('isLight');
      expect(result.current).toHaveProperty('toggleTheme');
    });

    it('has correct property types', () => {
      const mockSetTheme = vi.fn();
      mockUseNextTheme.mockReturnValue({
        theme: 'dark',
        setTheme: mockSetTheme,
        systemTheme: 'dark',
        resolvedTheme: 'dark',
      });

      const { result } = renderHook(() => useTheme());

      expect(typeof result.current.theme).toBe('string');
      expect(typeof result.current.setTheme).toBe('function');
      expect(typeof result.current.isDark).toBe('boolean');
      expect(typeof result.current.isLight).toBe('boolean');
      expect(typeof result.current.toggleTheme).toBe('function');
    });
  });
});
