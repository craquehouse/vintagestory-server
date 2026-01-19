import { describe, it, expect } from 'vitest';
import { cn, formatNumber } from './utils';

describe('utils', () => {
  describe('cn (className merger)', () => {
    it('merges multiple class strings', () => {
      expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('handles conditional classes (truthy values)', () => {
      expect(cn('foo', true && 'bar', 'baz')).toBe('foo bar baz');
    });

    it('handles conditional classes (falsy values)', () => {
      expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
    });

    it('handles undefined and null inputs', () => {
      expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
    });

    it('handles empty string inputs', () => {
      expect(cn('foo', '', 'bar')).toBe('foo bar');
    });

    it('handles no inputs', () => {
      expect(cn()).toBe('');
    });

    it('resolves Tailwind class conflicts (later wins)', () => {
      // tailwind-merge should resolve conflicts where later classes override earlier ones
      expect(cn('p-2', 'p-4')).toBe('p-4');
    });

    it('resolves Tailwind class conflicts (same property, different values)', () => {
      expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    });

    it('keeps non-conflicting Tailwind classes', () => {
      const result = cn('p-4', 'text-red-500', 'bg-blue-100');
      expect(result).toContain('p-4');
      expect(result).toContain('text-red-500');
      expect(result).toContain('bg-blue-100');
    });

    it('handles object syntax with conditional classes', () => {
      expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz');
    });

    it('handles array syntax', () => {
      expect(cn(['foo', 'bar'])).toBe('foo bar');
    });

    it('handles mixed object and string syntax', () => {
      expect(cn('base', { active: true, disabled: false })).toBe('base active');
    });
  });

  describe('formatNumber', () => {
    describe('numbers < 1000 (no suffix)', () => {
      it('formats 0', () => {
        expect(formatNumber(0)).toBe('0');
      });

      it('formats single digit numbers', () => {
        expect(formatNumber(5)).toBe('5');
      });

      it('formats double digit numbers', () => {
        expect(formatNumber(42)).toBe('42');
      });

      it('formats triple digit numbers', () => {
        expect(formatNumber(999)).toBe('999');
      });
    });

    describe('numbers >= 1000 (K suffix)', () => {
      it('formats exactly 1000 as "1.0K"', () => {
        expect(formatNumber(1000)).toBe('1.0K');
      });

      it('formats 1234 as "1.2K"', () => {
        expect(formatNumber(1234)).toBe('1.2K');
      });

      it('formats 5678 as "5.7K"', () => {
        expect(formatNumber(5678)).toBe('5.7K');
      });

      it('formats 999,999 as "1000.0K"', () => {
        expect(formatNumber(999999)).toBe('1000.0K');
      });

      it('rounds to 1 decimal place', () => {
        expect(formatNumber(1234)).toBe('1.2K'); // 1.234 -> 1.2
        expect(formatNumber(1567)).toBe('1.6K'); // 1.567 -> 1.6
        expect(formatNumber(1999)).toBe('2.0K'); // 1.999 -> 2.0
      });
    });

    describe('numbers >= 1,000,000 (M suffix)', () => {
      it('formats exactly 1,000,000 as "1.0M"', () => {
        expect(formatNumber(1000000)).toBe('1.0M');
      });

      it('formats 1,234,567 as "1.2M"', () => {
        expect(formatNumber(1234567)).toBe('1.2M');
      });

      it('formats 5,678,901 as "5.7M"', () => {
        expect(formatNumber(5678901)).toBe('5.7M');
      });

      it('rounds to 1 decimal place', () => {
        expect(formatNumber(1234567)).toBe('1.2M'); // 1.234567 -> 1.2
        expect(formatNumber(1567890)).toBe('1.6M'); // 1.56789 -> 1.6
        expect(formatNumber(1999999)).toBe('2.0M'); // 1.999999 -> 2.0
      });

      it('formats very large numbers', () => {
        expect(formatNumber(999999999)).toBe('1000.0M');
      });
    });

    describe('negative numbers', () => {
      it('formats negative numbers < 1000', () => {
        // formatNumber doesn't handle negatives specially, just returns string
        expect(formatNumber(-50)).toBe('-50');
      });

      it('does not format negative numbers with K suffix', () => {
        // >= checks don't trigger for negatives, returns string
        expect(formatNumber(-1234)).toBe('-1234');
      });

      it('does not format negative numbers with M suffix', () => {
        // >= checks don't trigger for negatives, returns string
        expect(formatNumber(-1234567)).toBe('-1234567');
      });
    });

    describe('boundary conditions', () => {
      it('formats 999 (just below K threshold)', () => {
        expect(formatNumber(999)).toBe('999');
      });

      it('formats 1000 (exactly at K threshold)', () => {
        expect(formatNumber(1000)).toBe('1.0K');
      });

      it('formats 999999 (just below M threshold)', () => {
        expect(formatNumber(999999)).toBe('1000.0K');
      });

      it('formats 1000000 (exactly at M threshold)', () => {
        expect(formatNumber(1000000)).toBe('1.0M');
      });
    });

    describe('decimal precision', () => {
      it('always shows 1 decimal place for K suffix', () => {
        expect(formatNumber(1000)).toBe('1.0K');
        expect(formatNumber(2000)).toBe('2.0K');
        expect(formatNumber(10000)).toBe('10.0K');
      });

      it('always shows 1 decimal place for M suffix', () => {
        expect(formatNumber(1000000)).toBe('1.0M');
        expect(formatNumber(2000000)).toBe('2.0M');
        expect(formatNumber(10000000)).toBe('10.0M');
      });
    });
  });
});
